"""Document ingestion pipeline.

Uploads local files to GCS and imports them into the Vertex AI RAG corpus.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import vertexai
from vertexai.preview import rag
from vertexai.preview.rag import RagCorpus

from src.config.settings import Settings
from src.utils.gcs import GCSClient

logger = logging.getLogger(__name__)

# Supported document extensions for ingestion
SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".docx", ".html", ".md")


class DocumentIngestor:
    """Upload documents to GCS and import them into the Vertex AI RAG corpus."""

    def __init__(self, settings: Settings, corpus: RagCorpus) -> None:
        self.settings = settings
        self.corpus = corpus
        self.gcs = GCSClient(project_id=settings.project_id)
        vertexai.init(project=settings.project_id, location=settings.region)

    # ------------------------------------------------------------------
    # High-level ingest methods
    # ------------------------------------------------------------------

    def ingest_local_file(
        self,
        local_path: str | Path,
        gcs_prefix: str = "uploads",
    ) -> rag.RagFile:
        """Upload a single local file to GCS then import it into the corpus.

        Args:
            local_path: Path to the local document.
            gcs_prefix: GCS object prefix (folder) within the raw-docs bucket.

        Returns:
            The imported :class:`rag.RagFile`.
        """
        local_path = Path(local_path)
        blob_name = f"{gcs_prefix}/{local_path.name}"
        gcs_uri = self.gcs.upload_file(
            local_path=local_path,
            bucket_name=self.settings.raw_docs_bucket,
            blob_name=blob_name,
        )
        return self.ingest_gcs_uri(gcs_uri)

    def ingest_local_directory(
        self,
        local_dir: str | Path,
        gcs_prefix: str = "uploads",
    ) -> list[rag.RagFile]:
        """Upload all supported documents in a directory and import them.

        Args:
            local_dir: Local directory containing documents.
            gcs_prefix: GCS object prefix within the raw-docs bucket.

        Returns:
            List of imported :class:`rag.RagFile` objects.
        """
        local_dir = Path(local_dir)
        uris = self.gcs.upload_directory(
            local_dir=local_dir,
            bucket_name=self.settings.raw_docs_bucket,
            prefix=gcs_prefix,
            extensions=SUPPORTED_EXTENSIONS,
        )
        rag_files: list[rag.RagFile] = []
        for uri in uris:
            try:
                rag_files.append(self.ingest_gcs_uri(uri))
            except Exception as exc:
                logger.error("Failed to ingest %s: %s", uri, exc)
        return rag_files

    def ingest_gcs_uri(self, gcs_uri: str) -> rag.RagFile:
        """Import a GCS object that already exists into the RAG corpus.

        Args:
            gcs_uri: A ``gs://bucket/path`` URI.

        Returns:
            The imported :class:`rag.RagFile`.
        """
        logger.info("Importing %s into corpus %s", gcs_uri, self.corpus.name)
        response = rag.import_files(
            corpus_name=self.corpus.name,
            paths=[gcs_uri],
            chunk_size=self.settings.rag_chunk_size,
            chunk_overlap=self.settings.rag_chunk_overlap,
        )
        logger.info(
            "Import complete: %d imported, %d failed",
            response.imported_rag_files_count,
            response.failed_rag_files_count,
        )
        if response.failed_rag_files_count > 0 and hasattr(response, "partial_failures"):
            for failure in response.partial_failures:
                logger.warning("Partial import failure: %s", failure)
        # Return the most recently added file
        files = list(rag.list_files(corpus_name=self.corpus.name))
        return files[-1] if files else None

    def ingest_gcs_prefix(self, gcs_prefix: str) -> list[rag.RagFile]:
        """Import all objects under a GCS prefix into the RAG corpus.

        Args:
            gcs_prefix: A ``gs://bucket/prefix`` URI or just a bucket path prefix
                        within the raw-docs bucket.

        Returns:
            List of all :class:`rag.RagFile` objects in the corpus after import.
        """
        if not gcs_prefix.startswith("gs://"):
            gcs_prefix = f"gs://{self.settings.raw_docs_bucket}/{gcs_prefix}"

        logger.info("Importing all files under %s", gcs_prefix)
        response = rag.import_files(
            corpus_name=self.corpus.name,
            paths=[gcs_prefix],
            chunk_size=self.settings.rag_chunk_size,
            chunk_overlap=self.settings.rag_chunk_overlap,
        )
        logger.info(
            "Bulk import complete: %d imported, %d failed",
            response.imported_rag_files_count,
            response.failed_rag_files_count,
        )
        return list(rag.list_files(corpus_name=self.corpus.name))
