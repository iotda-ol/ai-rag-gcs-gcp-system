"""Vertex AI RAG corpus management.

Wraps the Vertex AI RAG Engine API to create, list, and delete RAG corpora.
"""

from __future__ import annotations

import logging
from typing import Optional

import vertexai
from vertexai.preview import rag
from vertexai.preview.rag import RagCorpus

from src.config.settings import Settings

logger = logging.getLogger(__name__)


class CorpusManager:
    """Create and manage Vertex AI RAG corpora."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        vertexai.init(project=settings.project_id, location=settings.region)

    # ------------------------------------------------------------------
    # Corpus lifecycle
    # ------------------------------------------------------------------

    def get_or_create_corpus(self) -> RagCorpus:
        """Return the existing corpus or create one if it does not exist.

        The corpus resource name is read from ``settings.rag_corpus_name``.
        If that name is empty the corpus is looked up by display name; if
        still not found a new corpus is created.

        Returns:
            The :class:`RagCorpus` instance.
        """
        # 1. Try to fetch by resource name stored in settings / Secret Manager.
        if self.settings.rag_corpus_name:
            try:
                corpus = rag.get_corpus(name=self.settings.rag_corpus_name)
                logger.info("Found existing RAG corpus: %s", corpus.name)
                return corpus
            except Exception as exc:
                logger.warning("Could not fetch corpus by name '%s': %s", self.settings.rag_corpus_name, exc)

        # 2. Look up by display name.
        existing = self.list_corpora()
        display = self.settings.rag_corpus_display_name
        for corpus in existing:
            if corpus.display_name == display:
                logger.info("Found corpus by display name '%s': %s", display, corpus.name)
                return corpus

        # 3. Create a new corpus.
        logger.info("Creating new RAG corpus with display name '%s'", display)
        return self.create_corpus(display_name=display)

    def create_corpus(self, display_name: Optional[str] = None) -> RagCorpus:
        """Create a new RAG corpus.

        Args:
            display_name: Human-readable name (defaults to
                          ``settings.rag_corpus_display_name``).

        Returns:
            The newly created :class:`RagCorpus`.
        """
        display_name = display_name or self.settings.rag_corpus_display_name
        embedding_model_config = rag.EmbeddingModelConfig(
            publisher_model=f"publishers/google/models/{self.settings.embedding_model}",
        )
        corpus = rag.create_corpus(
            display_name=display_name,
            embedding_model_config=embedding_model_config,
        )
        logger.info("Created RAG corpus: %s", corpus.name)
        return corpus

    def list_corpora(self) -> list[RagCorpus]:
        """Return all RAG corpora in the configured project/region."""
        return list(rag.list_corpora())

    def delete_corpus(self, corpus_name: str) -> None:
        """Delete a RAG corpus by its full resource name."""
        rag.delete_corpus(name=corpus_name)
        logger.info("Deleted RAG corpus: %s", corpus_name)

    # ------------------------------------------------------------------
    # File management within a corpus
    # ------------------------------------------------------------------

    def list_corpus_files(self, corpus_name: str) -> list:
        """List all files ingested into a corpus."""
        return list(rag.list_files(corpus_name=corpus_name))

    def delete_corpus_file(self, corpus_name: str, rag_file_name: str) -> None:
        """Remove a single file from the corpus index."""
        rag.delete_file(name=rag_file_name)
        logger.info("Deleted RAG file '%s' from corpus '%s'", rag_file_name, corpus_name)
