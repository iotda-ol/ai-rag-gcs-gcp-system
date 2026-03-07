"""Application settings loaded entirely from Google Secret Manager.

Usage example::

    from src.config.settings import Settings

    settings = Settings.from_secret_manager(project_id="my-gcp-project")
    print(settings.region)          # "us-central1"
    print(settings.raw_docs_bucket) # "my-gcp-project-rag-raw-docs"

The *project_id* is the only value that cannot itself be stored in Secret
Manager (it's needed to bootstrap the client).  Everything else is fetched
from Secret Manager, keeping environment-specific configuration out of code
and container images.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from src.utils.secrets import SecretManagerClient, build_secret_client

logger = logging.getLogger(__name__)

_SECRET_PREFIX = "rag"


@dataclass
class Settings:
    """Strongly-typed application configuration."""

    # ── Identity ──────────────────────────────────────────────────────
    project_id: str
    region: str = "us-central1"
    environment: str = "dev"

    # ── GCS ───────────────────────────────────────────────────────────
    raw_docs_bucket: str = ""
    processed_docs_bucket: str = ""

    # ── Vertex AI / RAG ───────────────────────────────────────────────
    rag_corpus_name: str = ""          # full resource name set post-deploy
    rag_corpus_display_name: str = "rag-corpus"
    embedding_model: str = "text-embedding-005"
    generation_model: str = "gemini-1.5-flash-002"
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 100
    rag_retrieval_top_k: int = 10
    rag_vector_distance_threshold: float = 0.5

    # ── Service account ───────────────────────────────────────────────
    rag_sa_email: str = ""

    # ── API keys (operator-managed secrets) ───────────────────────────
    gemini_api_key: str = ""
    langchain_api_key: str = ""
    vertex_ai_endpoint_override: str = ""

    # ── Internal ──────────────────────────────────────────────────────
    _secret_client: Optional[SecretManagerClient] = field(default=None, repr=False, compare=False)

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def from_secret_manager(
        cls,
        project_id: Optional[str] = None,
        prefix: str = _SECRET_PREFIX,
    ) -> "Settings":
        """Bootstrap settings by fetching all values from Secret Manager.

        Args:
            project_id: GCP project ID.  Falls back to the ``GCP_PROJECT_ID``
                        environment variable if not provided.
            prefix: Secret ID prefix (default ``"rag"``).

        Returns:
            A fully populated :class:`Settings` instance.
        """
        if project_id is None:
            project_id = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise ValueError(
                "project_id must be supplied or GCP_PROJECT_ID / GOOGLE_CLOUD_PROJECT "
                "environment variable must be set."
            )

        client = build_secret_client(project_id=project_id, prefix=prefix)
        logger.info("Loading settings from Secret Manager (project=%s, prefix=%s)", project_id, prefix)

        def _s(key: str, default: str = "") -> str:
            return client.get_secret_or_default(key, default=default)

        def _i(key: str, default: int = 0) -> int:
            raw = _s(key)
            return int(raw) if raw else default

        def _f(key: str, default: float = 0.0) -> float:
            raw = _s(key)
            return float(raw) if raw else default

        return cls(
            project_id=project_id,
            region=_s("region", "us-central1"),
            environment=_s("environment", "dev"),
            raw_docs_bucket=_s("raw-docs-bucket"),
            processed_docs_bucket=_s("processed-docs-bucket"),
            rag_corpus_name=_s("rag-corpus-name"),
            rag_corpus_display_name=_s("rag-corpus-display-name", "rag-corpus"),
            embedding_model=_s("embedding-model", "text-embedding-005"),
            generation_model=_s("generation-model", "gemini-1.5-flash-002"),
            rag_chunk_size=_i("rag-chunk-size", 512),
            rag_chunk_overlap=_i("rag-chunk-overlap", 100),
            rag_retrieval_top_k=_i("rag-retrieval-top-k", 10),
            rag_vector_distance_threshold=_f("rag-vector-distance-threshold", 0.5),
            rag_sa_email=_s("rag-sa-email"),
            gemini_api_key=_s("gemini-api-key"),
            langchain_api_key=_s("langchain-api-key"),
            vertex_ai_endpoint_override=_s("vertex-ai-endpoint-override"),
            _secret_client=client,
        )

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables (useful for local dev / testing).

        Each setting maps to an upper-cased, underscore env var prefixed with
        ``RAG_``, e.g. ``RAG_REGION``, ``RAG_EMBEDDING_MODEL``.
        """
        project_id = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        return cls(
            project_id=project_id,
            region=os.environ.get("RAG_REGION", "us-central1"),
            environment=os.environ.get("RAG_ENVIRONMENT", "dev"),
            raw_docs_bucket=os.environ.get("RAG_RAW_DOCS_BUCKET", ""),
            processed_docs_bucket=os.environ.get("RAG_PROCESSED_DOCS_BUCKET", ""),
            rag_corpus_name=os.environ.get("RAG_CORPUS_NAME", ""),
            rag_corpus_display_name=os.environ.get("RAG_CORPUS_DISPLAY_NAME", "rag-corpus"),
            embedding_model=os.environ.get("RAG_EMBEDDING_MODEL", "text-embedding-005"),
            generation_model=os.environ.get("RAG_GENERATION_MODEL", "gemini-1.5-flash-002"),
            rag_chunk_size=int(os.environ.get("RAG_CHUNK_SIZE", "512")),
            rag_chunk_overlap=int(os.environ.get("RAG_CHUNK_OVERLAP", "100")),
            rag_retrieval_top_k=int(os.environ.get("RAG_RETRIEVAL_TOP_K", "10")),
            rag_vector_distance_threshold=float(os.environ.get("RAG_VECTOR_DISTANCE_THRESHOLD", "0.5")),
            rag_sa_email=os.environ.get("RAG_SA_EMAIL", ""),
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            langchain_api_key=os.environ.get("LANGCHAIN_API_KEY", ""),
            vertex_ai_endpoint_override=os.environ.get("RAG_VERTEX_AI_ENDPOINT_OVERRIDE", ""),
        )
