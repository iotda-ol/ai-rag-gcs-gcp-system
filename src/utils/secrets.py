"""Google Secret Manager helper.

All application configuration is stored in Secret Manager so the only
runtime credential needed is the GCP project ID (equivalent to aws_profile).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from google.api_core.exceptions import NotFound
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class SecretManagerClient:
    """Thin wrapper around the Secret Manager client with caching and prefix support."""

    def __init__(self, project_id: str, prefix: str = "rag") -> None:
        """
        Args:
            project_id: GCP project ID.
            prefix: Secret ID prefix (e.g. ``"rag"``).  All secrets are stored
                    as ``<prefix>-<key>``.
        """
        self.project_id = project_id
        self.prefix = prefix
        self._client = secretmanager.SecretManagerServiceClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_secret(self, key: str, version: str = "latest") -> str:
        """Return the latest version of a secret value.

        Args:
            key: Logical key (e.g. ``"region"``).  The full secret ID is
                 ``<prefix>-<key>``.
            version: Secret version, default ``"latest"``.

        Returns:
            The secret payload as a UTF-8 string.

        Raises:
            KeyError: If the secret does not exist.
        """
        secret_id = self._secret_id(key)
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
        try:
            response = self._access_secret_version(name)
            return response.payload.data.decode("utf-8")
        except NotFound:
            raise KeyError(f"Secret '{secret_id}' not found in project '{self.project_id}'")

    def get_secret_or_default(self, key: str, default: str = "", version: str = "latest") -> str:
        """Return a secret value, or *default* if the secret does not exist."""
        try:
            return self.get_secret(key, version=version)
        except KeyError:
            logger.debug("Secret '%s' not found; using default.", key)
            return default

    def get_int(self, key: str, version: str = "latest") -> int:
        """Return a secret value parsed as an integer."""
        return int(self.get_secret(key, version=version))

    def get_float(self, key: str, version: str = "latest") -> float:
        """Return a secret value parsed as a float."""
        return float(self.get_secret(key, version=version))

    def get_bool(self, key: str, version: str = "latest") -> bool:
        """Return a secret value parsed as a boolean (``"true"``/``"false"``)."""
        return self.get_secret(key, version=version).strip().lower() in {"true", "1", "yes"}

    def list_secrets(self) -> list[str]:
        """Return all secret IDs under the configured prefix."""
        parent = f"projects/{self.project_id}"
        filter_str = f'name:"{self.prefix}-"'
        secrets = self._client.list_secrets(request={"parent": parent, "filter": filter_str})
        return [s.name.split("/")[-1] for s in secrets]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _secret_id(self, key: str) -> str:
        return f"{self.prefix}-{key}"

    @lru_cache(maxsize=256)
    def _access_secret_version(self, name: str):
        """Cached call to Secret Manager; avoids redundant API round-trips."""
        return self._client.access_secret_version(request={"name": name})


def build_secret_client(project_id: str, prefix: str = "rag") -> SecretManagerClient:
    """Factory that returns a :class:`SecretManagerClient` for *project_id*."""
    return SecretManagerClient(project_id=project_id, prefix=prefix)
