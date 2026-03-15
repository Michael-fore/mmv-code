"""Local filesystem mock for Google Cloud Storage.

Mirrors the subset of the ``google.cloud.storage`` SDK used by
:pymod:`mmv-data.tools.gcs` so that upload/dedup logic can be exercised
without GCP credentials.  Files are persisted under ``/tmp/mmv_gcs_mock/``
in a directory tree that mirrors ``gs://<bucket>/<prefix>/<object>``.

This module exposes ``MockBlob``, ``MockBucket``, and ``MockClient`` — all
duck-typed against the real ``google.cloud.storage`` counterparts for the
methods we actually call.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Iterator

_MOCK_ROOT = Path("/tmp/mmv_gcs_mock")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metadata_path(blob_path: Path) -> Path:
    """Return the sidecar metadata JSON path for a blob file."""
    return blob_path.with_suffix(blob_path.suffix + ".__meta__.json")


# ---------------------------------------------------------------------------
# MockBlob
# ---------------------------------------------------------------------------

class MockBlob:
    """Minimal stand-in for ``google.cloud.storage.Blob``."""

    def __init__(self, name: str, bucket: "MockBucket") -> None:
        self.name: str = name
        self.bucket: MockBucket = bucket
        self.metadata: dict[str, str] | None = None
        self._local_path: Path = _MOCK_ROOT / bucket.name / name

    # -- upload / download --------------------------------------------------

    def upload_from_filename(self, filename: str) -> None:
        """Copy *filename* into the mock store and persist metadata."""
        self._local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filename, self._local_path)
        self._write_metadata()

    def download_to_filename(self, filename: str) -> None:
        """Copy the mock blob to a local path."""
        dest = Path(filename)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._local_path, dest)

    # -- metadata -----------------------------------------------------------

    def reload(self) -> None:
        """Load metadata from the sidecar JSON (no-op if missing)."""
        meta_file = _metadata_path(self._local_path)
        if meta_file.exists():
            self.metadata = json.loads(meta_file.read_text())

    def patch(self) -> None:
        """Persist current ``self.metadata`` to the sidecar JSON."""
        self._write_metadata()

    # -- existence ----------------------------------------------------------

    def exists(self) -> bool:
        return self._local_path.exists()

    # -- internal -----------------------------------------------------------

    def _write_metadata(self) -> None:
        if self.metadata:
            meta_file = _metadata_path(self._local_path)
            meta_file.write_text(json.dumps(self.metadata, indent=2))


# ---------------------------------------------------------------------------
# MockBucket
# ---------------------------------------------------------------------------

class MockBucket:
    """Minimal stand-in for ``google.cloud.storage.Bucket``."""

    def __init__(self, name: str) -> None:
        self.name: str = name
        self._root: Path = _MOCK_ROOT / name

    def blob(self, blob_name: str) -> MockBlob:
        return MockBlob(blob_name, self)

    def list_blobs(self, prefix: str | None = None) -> Iterator[MockBlob]:
        """Yield ``MockBlob`` instances whose names start with *prefix*.

        Walks the local directory tree and reconstructs blob names relative
        to the bucket root.
        """
        search_root = self._root / prefix if prefix else self._root
        if not search_root.exists():
            return

        for file_path in search_root.rglob("*"):
            # Skip sidecar metadata files and directories.
            if file_path.is_dir() or ".__meta__.json" in file_path.name:
                continue
            blob_name = str(file_path.relative_to(self._root))
            blob = MockBlob(blob_name, self)
            blob.reload()
            yield blob


# ---------------------------------------------------------------------------
# MockClient
# ---------------------------------------------------------------------------

class MockClient:
    """Minimal stand-in for ``google.cloud.storage.Client``.

    Usage::

        from mmv_data.tools.gcs_local import MockClient
        client = MockClient()
        bucket = client.bucket("mmv-raw-data")
    """

    def __init__(self, project: str = "mmv-cloud") -> None:
        self.project: str = project
        _MOCK_ROOT.mkdir(parents=True, exist_ok=True)

    def bucket(self, bucket_name: str) -> MockBucket:
        return MockBucket(bucket_name)
