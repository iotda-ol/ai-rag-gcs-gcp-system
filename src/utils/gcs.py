"""Google Cloud Storage helpers for the RAG pipeline."""

from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path
from typing import Generator, Optional

from google.cloud import storage
from google.cloud.storage import Blob, Bucket

logger = logging.getLogger(__name__)


class GCSClient:
    """Thin wrapper around the GCS client with upload / download helpers."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self._client = storage.Client(project=project_id)

    # ------------------------------------------------------------------
    # Bucket helpers
    # ------------------------------------------------------------------

    def get_bucket(self, bucket_name: str) -> Bucket:
        return self._client.bucket(bucket_name)

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------

    def upload_file(
        self,
        local_path: str | Path,
        bucket_name: str,
        blob_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a local file to GCS.

        Args:
            local_path: Path to the local file.
            bucket_name: Destination bucket name.
            blob_name: Destination object name; defaults to the file's basename.
            content_type: MIME type; auto-detected if not provided.

        Returns:
            GCS URI of the uploaded object (``gs://bucket/blob``).
        """
        local_path = Path(local_path)
        if blob_name is None:
            blob_name = local_path.name
        if content_type is None:
            content_type, _ = mimetypes.guess_type(str(local_path))
            content_type = content_type or "application/octet-stream"

        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(local_path), content_type=content_type)
        uri = f"gs://{bucket_name}/{blob_name}"
        logger.info("Uploaded %s → %s", local_path, uri)
        return uri

    def upload_directory(
        self,
        local_dir: str | Path,
        bucket_name: str,
        prefix: str = "",
        extensions: Optional[tuple[str, ...]] = None,
    ) -> list[str]:
        """Recursively upload all files in *local_dir* to GCS.

        Args:
            local_dir: Local directory to upload.
            bucket_name: Destination bucket name.
            prefix: Optional GCS object prefix (folder path).
            extensions: If provided, only files with these extensions are uploaded
                        (e.g. ``(".pdf", ".txt")``).

        Returns:
            List of GCS URIs for all uploaded objects.
        """
        local_dir = Path(local_dir)
        uris: list[str] = []
        for file_path in local_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if extensions and file_path.suffix.lower() not in extensions:
                continue
            relative = file_path.relative_to(local_dir)
            blob_name = f"{prefix}/{relative}".lstrip("/") if prefix else str(relative)
            uris.append(self.upload_file(file_path, bucket_name, blob_name=blob_name))
        return uris

    # ------------------------------------------------------------------
    # Download helpers
    # ------------------------------------------------------------------

    def download_file(
        self,
        bucket_name: str,
        blob_name: str,
        local_path: str | Path,
    ) -> Path:
        """Download a GCS object to a local file."""
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(str(local_path))
        logger.info("Downloaded gs://%s/%s → %s", bucket_name, blob_name, local_path)
        return local_path

    # ------------------------------------------------------------------
    # List / delete helpers
    # ------------------------------------------------------------------

    def list_blobs(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
        extensions: Optional[tuple[str, ...]] = None,
    ) -> list[Blob]:
        """Return blobs in *bucket_name*, optionally filtered by prefix / extension."""
        blobs = list(self._client.list_blobs(bucket_name, prefix=prefix))
        if extensions:
            blobs = [b for b in blobs if any(b.name.lower().endswith(ext) for ext in extensions)]
        return blobs

    def delete_blob(self, bucket_name: str, blob_name: str) -> None:
        """Delete a single GCS object."""
        bucket = self.get_bucket(bucket_name)
        bucket.blob(blob_name).delete()
        logger.info("Deleted gs://%s/%s", bucket_name, blob_name)

    def gcs_uri_to_parts(self, uri: str) -> tuple[str, str]:
        """Parse ``gs://bucket/path`` into ``(bucket, path)``."""
        if not uri.startswith("gs://"):
            raise ValueError(f"Not a valid GCS URI: {uri}")
        without_scheme = uri[5:]
        bucket, _, path = without_scheme.partition("/")
        return bucket, path
