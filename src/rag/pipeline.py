"""End-to-end RAG pipeline orchestrating ingestion and retrieval."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.config.settings import Settings
from src.rag.corpus import CorpusManager
from src.rag.ingestor import DocumentIngestor
from src.rag.retriever import RAGResponse, RAGRetriever

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Facade that wires together corpus management, ingestion, and retrieval.

    Usage::

        pipeline = RAGPipeline.from_project("my-gcp-project")

        # Ingest documents
        pipeline.ingest_directory("/path/to/docs")

        # Query
        response = pipeline.query("What is the return policy?")
        print(response.answer)
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._corpus_manager = CorpusManager(settings)
        self._corpus = None
        self._ingestor: Optional[DocumentIngestor] = None
        self._retriever: Optional[RAGRetriever] = None

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def from_project(
        cls,
        project_id: str,
        use_secret_manager: bool = True,
    ) -> "RAGPipeline":
        """Build a :class:`RAGPipeline` using *project_id* as the only required input.

        Args:
            project_id: GCP project ID (the only required parameter).
            use_secret_manager: If ``True`` (default), load all other settings
                                from Google Secret Manager.  If ``False``, fall
                                back to environment variables (useful for local
                                development / testing).

        Returns:
            A fully configured :class:`RAGPipeline`.
        """
        if use_secret_manager:
            settings = Settings.from_secret_manager(project_id=project_id)
        else:
            import os
            os.environ.setdefault("GCP_PROJECT_ID", project_id)
            settings = Settings.from_env()
        return cls(settings=settings)

    # ------------------------------------------------------------------
    # Corpus
    # ------------------------------------------------------------------

    def _ensure_corpus(self):
        if self._corpus is None:
            self._corpus = self._corpus_manager.get_or_create_corpus()
            self._ingestor = DocumentIngestor(settings=self.settings, corpus=self._corpus)
            self._retriever = RAGRetriever(settings=self.settings, corpus=self._corpus)
        return self._corpus

    @property
    def corpus(self):
        return self._ensure_corpus()

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_file(self, local_path: str | Path, gcs_prefix: str = "uploads") -> None:
        """Upload a single file to GCS and import it into the RAG corpus.

        Args:
            local_path: Path to the local document (PDF, TXT, DOCX, HTML, MD).
            gcs_prefix: GCS object prefix within the raw-docs bucket.
        """
        self._ensure_corpus()
        rag_file = self._ingestor.ingest_local_file(local_path, gcs_prefix=gcs_prefix)
        logger.info("Ingested file: %s", rag_file)

    def ingest_directory(self, local_dir: str | Path, gcs_prefix: str = "uploads") -> None:
        """Upload all supported documents in a directory to GCS and import them.

        Args:
            local_dir: Directory of documents to ingest.
            gcs_prefix: GCS object prefix within the raw-docs bucket.
        """
        self._ensure_corpus()
        rag_files = self._ingestor.ingest_local_directory(local_dir, gcs_prefix=gcs_prefix)
        logger.info("Ingested %d files from %s", len(rag_files), local_dir)

    def ingest_gcs_prefix(self, gcs_prefix: str) -> None:
        """Import all objects under a GCS prefix into the RAG corpus.

        Args:
            gcs_prefix: GCS path prefix, e.g. ``"gs://bucket/folder"`` or just
                        ``"folder"`` (uses the raw-docs bucket).
        """
        self._ensure_corpus()
        rag_files = self._ingestor.ingest_gcs_prefix(gcs_prefix)
        logger.info("Ingested %d files from GCS prefix '%s'", len(rag_files), gcs_prefix)

    # ------------------------------------------------------------------
    # Query / Generation
    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        system_instruction: Optional[str] = None,
    ) -> RAGResponse:
        """Ask a question and get a grounded answer.

        Args:
            question: Natural-language question.
            system_instruction: Optional system prompt for the generative model.

        Returns:
            A :class:`RAGResponse` with the answer and supporting source chunks.
        """
        self._ensure_corpus()
        response = self._retriever.generate(question, system_instruction=system_instruction)
        return response

    def retrieve(self, query: str):
        """Retrieve relevant context chunks without generation.

        Args:
            query: Search string or question.

        Returns:
            List of :class:`~src.rag.retriever.RetrievalResult` objects.
        """
        self._ensure_corpus()
        return self._retriever.retrieve(query)
