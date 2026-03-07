"""Tests for src.utils.secrets and src.config.settings."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_secret_response(value: str):
    """Return a mock Secret Manager access_secret_version response."""
    mock_response = MagicMock()
    mock_response.payload.data = value.encode("utf-8")
    return mock_response


# ---------------------------------------------------------------------------
# SecretManagerClient
# ---------------------------------------------------------------------------

class TestSecretManagerClient:
    @patch("src.utils.secrets.secretmanager.SecretManagerServiceClient")
    def test_get_secret_success(self, mock_client_cls):
        from src.utils.secrets import SecretManagerClient

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.access_secret_version.return_value = _make_secret_response("us-central1")

        client = SecretManagerClient(project_id="test-project", prefix="rag")
        # Clear lru_cache so the mock is actually called
        client._access_secret_version.cache_clear()

        value = client.get_secret("region")
        assert value == "us-central1"

    @patch("src.utils.secrets.secretmanager.SecretManagerServiceClient")
    def test_get_secret_not_found_raises_key_error(self, mock_client_cls):
        from google.api_core.exceptions import NotFound
        from src.utils.secrets import SecretManagerClient

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.access_secret_version.side_effect = NotFound("not found")

        client = SecretManagerClient(project_id="test-project", prefix="rag")
        client._access_secret_version.cache_clear()

        with pytest.raises(KeyError, match="rag-missing"):
            client.get_secret("missing")

    @patch("src.utils.secrets.secretmanager.SecretManagerServiceClient")
    def test_get_secret_or_default_returns_default_on_missing(self, mock_client_cls):
        from google.api_core.exceptions import NotFound
        from src.utils.secrets import SecretManagerClient

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.access_secret_version.side_effect = NotFound("not found")

        client = SecretManagerClient(project_id="test-project", prefix="rag")
        client._access_secret_version.cache_clear()

        result = client.get_secret_or_default("missing", default="fallback")
        assert result == "fallback"

    @patch("src.utils.secrets.secretmanager.SecretManagerServiceClient")
    def test_get_int_parses_integer(self, mock_client_cls):
        from src.utils.secrets import SecretManagerClient

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.access_secret_version.return_value = _make_secret_response("512")

        client = SecretManagerClient(project_id="test-project", prefix="rag")
        client._access_secret_version.cache_clear()

        assert client.get_int("rag-chunk-size") == 512

    @patch("src.utils.secrets.secretmanager.SecretManagerServiceClient")
    def test_get_float_parses_float(self, mock_client_cls):
        from src.utils.secrets import SecretManagerClient

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.access_secret_version.return_value = _make_secret_response("0.5")

        client = SecretManagerClient(project_id="test-project", prefix="rag")
        client._access_secret_version.cache_clear()

        assert client.get_float("vector-distance") == pytest.approx(0.5)

    @patch("src.utils.secrets.secretmanager.SecretManagerServiceClient")
    def test_secret_id_uses_prefix(self, mock_client_cls):
        from src.utils.secrets import SecretManagerClient

        client = SecretManagerClient(project_id="test-project", prefix="myapp")
        assert client._secret_id("region") == "myapp-region"

    def test_build_secret_client_factory(self):
        with patch("src.utils.secrets.secretmanager.SecretManagerServiceClient"):
            from src.utils.secrets import build_secret_client

            client = build_secret_client("test-project", prefix="rag")
            assert client.project_id == "test-project"
            assert client.prefix == "rag"


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class TestSettingsFromEnv:
    def test_from_env_defaults(self):
        from src.config.settings import Settings

        env_patch = {
            "GCP_PROJECT_ID": "env-project",
            "RAG_REGION": "europe-west1",
            "RAG_EMBEDDING_MODEL": "text-embedding-004",
        }
        with patch.dict(os.environ, env_patch, clear=False):
            settings = Settings.from_env()

        assert settings.project_id == "env-project"
        assert settings.region == "europe-west1"
        assert settings.embedding_model == "text-embedding-004"
        # Defaults
        assert settings.rag_chunk_size == 512
        assert settings.rag_retrieval_top_k == 10

    def test_from_env_raises_without_project(self):
        """from_secret_manager should raise if no project_id can be determined."""
        cleaned = {k: v for k, v in os.environ.items()
                   if k not in ("GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT")}
        with patch.dict(os.environ, cleaned, clear=True):
            with pytest.raises(ValueError, match="project_id must be supplied"):
                with patch("src.utils.secrets.secretmanager.SecretManagerServiceClient"):
                    from src.config.settings import Settings
                    Settings.from_secret_manager()  # no project_id arg, no env var

    def test_chunk_size_and_overlap_types(self):
        from src.config.settings import Settings

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "p", "RAG_CHUNK_SIZE": "256", "RAG_CHUNK_OVERLAP": "50"}):
            settings = Settings.from_env()

        assert isinstance(settings.rag_chunk_size, int)
        assert settings.rag_chunk_size == 256
        assert settings.rag_chunk_overlap == 50

    @patch("src.utils.secrets.secretmanager.SecretManagerServiceClient")
    def test_from_secret_manager(self, mock_client_cls):
        from src.config.settings import Settings

        secret_values = {
            "rag-region": "asia-east1",
            "rag-environment": "prod",
            "rag-raw-docs-bucket": "my-project-rag-raw-docs",
            "rag-processed-docs-bucket": "my-project-rag-processed-docs",
            "rag-rag-corpus-name": "projects/p/locations/l/ragCorpora/123",
            "rag-rag-corpus-display-name": "rag-corpus",
            "rag-embedding-model": "text-embedding-005",
            "rag-generation-model": "gemini-1.5-flash-002",
            "rag-rag-chunk-size": "512",
            "rag-rag-chunk-overlap": "100",
            "rag-rag-retrieval-top-k": "10",
            "rag-rag-vector-distance-threshold": "0.5",
            "rag-rag-sa-email": "rag-pipeline-sa@my-project.iam.gserviceaccount.com",
            "rag-gemini-api-key": "",
            "rag-langchain-api-key": "",
            "rag-vertex-ai-endpoint-override": "",
        }

        def _access(request):
            name = request["name"]
            secret_id = name.split("/secrets/")[1].split("/versions/")[0]
            key = secret_id  # already prefixed with "rag-"
            return _make_secret_response(secret_values.get(key, ""))

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.access_secret_version.side_effect = _access

        settings = Settings.from_secret_manager(project_id="my-project")

        assert settings.project_id == "my-project"
        assert settings.region == "asia-east1"
        assert settings.environment == "prod"
        assert settings.raw_docs_bucket == "my-project-rag-raw-docs"
        assert settings.rag_chunk_size == 512


# ---------------------------------------------------------------------------
# GCSClient (unit)
# ---------------------------------------------------------------------------

class TestGCSClient:
    @patch("src.utils.gcs.storage.Client")
    def test_gcs_uri_to_parts(self, _mock_storage):
        from src.utils.gcs import GCSClient

        client = GCSClient(project_id="test-project")
        bucket, path = client.gcs_uri_to_parts("gs://my-bucket/folder/file.pdf")
        assert bucket == "my-bucket"
        assert path == "folder/file.pdf"

    @patch("src.utils.gcs.storage.Client")
    def test_gcs_uri_to_parts_invalid(self, _mock_storage):
        from src.utils.gcs import GCSClient

        client = GCSClient(project_id="test-project")
        with pytest.raises(ValueError, match="Not a valid GCS URI"):
            client.gcs_uri_to_parts("s3://bucket/key")

    @patch("src.utils.gcs.storage.Client")
    def test_upload_file(self, mock_storage_cls):
        import tempfile

        from src.utils.gcs import GCSClient

        mock_client = MagicMock()
        mock_storage_cls.return_value = mock_client
        mock_blob = MagicMock()
        mock_client.bucket.return_value.blob.return_value = mock_blob

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"hello")
            tmp_path = f.name

        try:
            gcs = GCSClient(project_id="test-project")
            uri = gcs.upload_file(tmp_path, "my-bucket", blob_name="test/hello.txt")
            assert uri == "gs://my-bucket/test/hello.txt"
            mock_blob.upload_from_filename.assert_called_once()
        finally:
            os.unlink(tmp_path)
