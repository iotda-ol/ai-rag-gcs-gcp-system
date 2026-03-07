"""Tests for the RAG pipeline components (corpus, ingestor, retriever, pipeline)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_settings():
    from src.config.settings import Settings

    return Settings(
        project_id="test-project",
        region="us-central1",
        environment="test",
        raw_docs_bucket="test-project-rag-raw-docs",
        processed_docs_bucket="test-project-rag-processed-docs",
        rag_corpus_name="projects/test-project/locations/us-central1/ragCorpora/123",
        rag_corpus_display_name="rag-corpus",
        embedding_model="text-embedding-005",
        generation_model="gemini-1.5-flash-002",
        rag_chunk_size=512,
        rag_chunk_overlap=100,
        rag_retrieval_top_k=10,
        rag_vector_distance_threshold=0.5,
        rag_sa_email="sa@test-project.iam.gserviceaccount.com",
    )


@pytest.fixture()
def mock_corpus():
    corpus = MagicMock()
    corpus.name = "projects/test-project/locations/us-central1/ragCorpora/123"
    corpus.display_name = "rag-corpus"
    return corpus


# ---------------------------------------------------------------------------
# CorpusManager
# ---------------------------------------------------------------------------

class TestCorpusManager:
    @patch("src.rag.corpus.vertexai.init")
    @patch("src.rag.corpus.rag")
    def test_get_or_create_corpus_uses_existing(self, mock_rag, mock_init, mock_settings, mock_corpus):
        from src.rag.corpus import CorpusManager

        mock_rag.get_corpus.return_value = mock_corpus

        manager = CorpusManager(settings=mock_settings)
        corpus = manager.get_or_create_corpus()

        mock_rag.get_corpus.assert_called_once_with(name=mock_settings.rag_corpus_name)
        assert corpus.name == mock_corpus.name

    @patch("src.rag.corpus.vertexai.init")
    @patch("src.rag.corpus.rag")
    def test_get_or_create_corpus_creates_when_not_found(self, mock_rag, mock_init, mock_settings, mock_corpus):
        from src.rag.corpus import CorpusManager

        mock_rag.get_corpus.side_effect = Exception("not found")
        mock_rag.list_corpora.return_value = []
        mock_rag.create_corpus.return_value = mock_corpus
        mock_rag.EmbeddingModelConfig.return_value = MagicMock()

        manager = CorpusManager(settings=mock_settings)
        corpus = manager.get_or_create_corpus()

        mock_rag.create_corpus.assert_called_once()
        assert corpus == mock_corpus

    @patch("src.rag.corpus.vertexai.init")
    @patch("src.rag.corpus.rag")
    def test_list_corpora(self, mock_rag, mock_init, mock_settings, mock_corpus):
        from src.rag.corpus import CorpusManager

        mock_rag.list_corpora.return_value = [mock_corpus]

        manager = CorpusManager(settings=mock_settings)
        result = manager.list_corpora()

        assert result == [mock_corpus]

    @patch("src.rag.corpus.vertexai.init")
    @patch("src.rag.corpus.rag")
    def test_delete_corpus(self, mock_rag, mock_init, mock_settings):
        from src.rag.corpus import CorpusManager

        manager = CorpusManager(settings=mock_settings)
        manager.delete_corpus("projects/.../ragCorpora/123")

        mock_rag.delete_corpus.assert_called_once_with(name="projects/.../ragCorpora/123")


# ---------------------------------------------------------------------------
# DocumentIngestor
# ---------------------------------------------------------------------------

class TestDocumentIngestor:
    @patch("src.rag.ingestor.vertexai.init")
    @patch("src.rag.ingestor.rag")
    @patch("src.rag.ingestor.GCSClient")
    def test_ingest_gcs_uri(self, mock_gcs_cls, mock_rag, mock_init, mock_settings, mock_corpus):
        import tempfile

        from src.rag.ingestor import DocumentIngestor

        mock_response = MagicMock()
        mock_response.imported_rag_files_count = 1
        mock_response.failed_rag_files_count = 0
        mock_rag.import_files.return_value = mock_response

        mock_rag_file = MagicMock()
        mock_rag_file.name = "projects/.../ragFiles/abc"
        mock_rag.list_files.return_value = [mock_rag_file]

        ingestor = DocumentIngestor(settings=mock_settings, corpus=mock_corpus)
        result = ingestor.ingest_gcs_uri("gs://test-project-rag-raw-docs/uploads/doc.pdf")

        mock_rag.import_files.assert_called_once()
        call_kwargs = mock_rag.import_files.call_args
        assert call_kwargs.kwargs["corpus_name"] == mock_corpus.name
        assert result == mock_rag_file

    @patch("src.rag.ingestor.vertexai.init")
    @patch("src.rag.ingestor.rag")
    @patch("src.rag.ingestor.GCSClient")
    def test_ingest_gcs_prefix_prepends_gs_scheme(self, mock_gcs_cls, mock_rag, mock_init, mock_settings, mock_corpus):
        from src.rag.ingestor import DocumentIngestor

        mock_response = MagicMock()
        mock_response.imported_rag_files_count = 2
        mock_response.failed_rag_files_count = 0
        mock_rag.import_files.return_value = mock_response
        mock_rag.list_files.return_value = []

        ingestor = DocumentIngestor(settings=mock_settings, corpus=mock_corpus)
        ingestor.ingest_gcs_prefix("uploads/docs")

        call_kwargs = mock_rag.import_files.call_args
        expected_path = f"gs://{mock_settings.raw_docs_bucket}/uploads/docs"
        assert call_kwargs.kwargs["paths"] == [expected_path]


# ---------------------------------------------------------------------------
# RAGRetriever
# ---------------------------------------------------------------------------

class TestRAGRetriever:
    @patch("src.rag.retriever.vertexai.init")
    @patch("src.rag.retriever.rag")
    def test_retrieve_returns_results(self, mock_rag, mock_init, mock_settings, mock_corpus):
        from src.rag.retriever import RAGRetriever

        mock_ctx = MagicMock()
        mock_ctx.text = "Some relevant text."
        mock_ctx.source_uri = "gs://bucket/file.pdf"
        mock_ctx.score = 0.92

        mock_response = MagicMock()
        mock_response.contexts.contexts = [mock_ctx]
        mock_rag.retrieval_query.return_value = mock_response
        mock_rag.RagResource = MagicMock()

        retriever = RAGRetriever(settings=mock_settings, corpus=mock_corpus)
        results = retriever.retrieve("What is the return policy?")

        assert len(results) == 1
        assert results[0].text == "Some relevant text."
        assert results[0].score == pytest.approx(0.92)
        assert results[0].source_uri == "gs://bucket/file.pdf"

    @patch("src.rag.retriever.vertexai.init")
    @patch("src.rag.retriever.rag")
    @patch("src.rag.retriever.GenerativeModel")
    @patch("src.rag.retriever.Tool")
    def test_generate_returns_rag_response(self, mock_tool, mock_model_cls, mock_rag, mock_init, mock_settings, mock_corpus):
        from src.rag.retriever import RAGRetriever

        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        mock_model.generate_content.return_value.text = "The return policy is 30 days."

        mock_ctx = MagicMock()
        mock_ctx.text = "Return policy details."
        mock_ctx.source_uri = "gs://bucket/policy.pdf"
        mock_ctx.score = 0.85
        mock_response = MagicMock()
        mock_response.contexts.contexts = [mock_ctx]
        mock_rag.retrieval_query.return_value = mock_response
        mock_rag.RagResource = MagicMock()
        mock_rag.Retrieval = MagicMock()
        mock_rag.VertexRagStore = MagicMock()

        retriever = RAGRetriever(settings=mock_settings, corpus=mock_corpus)
        response = retriever.generate("What is the return policy?")

        assert response.answer == "The return policy is 30 days."
        assert response.model == mock_settings.generation_model
        assert response.query == "What is the return policy?"


# ---------------------------------------------------------------------------
# RAGPipeline
# ---------------------------------------------------------------------------

class TestRAGPipeline:
    @patch("src.rag.pipeline.CorpusManager")
    @patch("src.rag.pipeline.Settings")
    def test_from_project_uses_secret_manager(self, mock_settings_cls, mock_corpus_mgr_cls):
        """from_project() delegates to Settings.from_secret_manager."""
        from src.rag.pipeline import RAGPipeline

        mock_settings = MagicMock()
        mock_settings_cls.from_secret_manager.return_value = mock_settings

        pipeline = RAGPipeline.from_project("my-project", use_secret_manager=True)

        mock_settings_cls.from_secret_manager.assert_called_once_with(project_id="my-project")
        assert pipeline.settings == mock_settings

    @patch("src.rag.pipeline.CorpusManager")
    @patch("src.rag.pipeline.DocumentIngestor")
    @patch("src.rag.pipeline.RAGRetriever")
    def test_query_calls_retriever(self, mock_retriever_cls, mock_ingestor_cls, mock_corpus_mgr_cls, mock_settings, mock_corpus):
        from src.rag.pipeline import RAGPipeline
        from src.rag.retriever import RAGResponse

        mock_corpus_mgr = MagicMock()
        mock_corpus_mgr.get_or_create_corpus.return_value = mock_corpus
        mock_corpus_mgr_cls.return_value = mock_corpus_mgr

        mock_retriever = MagicMock()
        expected_response = RAGResponse(
            query="What?",
            answer="42",
            retrieved_chunks=[],
            model="gemini-1.5-flash-002",
        )
        mock_retriever.generate.return_value = expected_response
        mock_retriever_cls.return_value = mock_retriever

        pipeline = RAGPipeline(settings=mock_settings)
        response = pipeline.query("What?")

        mock_retriever.generate.assert_called_once_with("What?", system_instruction=None)
        assert response.answer == "42"
