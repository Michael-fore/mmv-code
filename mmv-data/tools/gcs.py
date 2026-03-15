"""GCS upload and content-hash deduplication layer for the MMV platform.

Architecture rule: "Raw files -> GCS first. Deduplicate before storing —
use content hashing."  Every uploaded object carries its SHA-256 content
hash in GCS custom metadata (``x-mmv-content-sha256``).  Before uploading,
we scan existing objects under the target prefix for a matching hash;
duplicates are skipped unless the caller explicitly opts out.

Target bucket: gs://mmv-raw-data/
GCP project  : mmv-cloud

Usage with real GCS::

    from google.cloud import storage
    from mmv_data.tools.gcs import upload_to_gcs

    client = storage.Client(project="mmv-cloud")
    result = upload_to_gcs("data.json", "mmv-raw-data", "rent/2024/", client=client)

Usage with local mock (no credentials required)::

    from mmv_data.tools.gcs_local import MockClient
    from mmv_data.tools.gcs import upload_to_gcs

    result = upload_to_gcs("data.json", "mmv-raw-data", "rent/2024/", client=MockClient())
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# The GCS metadata key we use to store the content hash on every object.
_HASH_META_KEY = "x-mmv-content-sha256"

# Default target bucket per architecture rules.
DEFAULT_BUCKET = "mmv-raw-data"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _get_client(client: Any | None = None) -> Any:
    """Return *client* as-is, or construct a real ``storage.Client``.

    Lazily imports ``google.cloud.storage`` so the module can be loaded
    even when the SDK is not installed (e.g. during mock-only testing).
    """
    if client is not None:
        return client
    from google.cloud import storage  # type: ignore[import-untyped]
    return storage.Client(project="mmv-cloud")


def compute_content_hash(file_path: str) -> str:
    """Return the hex-encoded SHA-256 digest of a file's contents.

    Args:
        file_path: Path to the file on the local filesystem.

    Returns:
        A 64-character lowercase hex string.

    Raises:
        FileNotFoundError: If *file_path* does not exist.
    """
    sha = hashlib.sha256()
    with open(file_path, "rb") as fh:
        while True:
            chunk = fh.read(8192)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def is_duplicate(
    local_path: str,
    bucket: str,
    prefix: str,
    client: Any | None = None,
) -> bool:
    """Check whether a file with the same content hash already exists in GCS.

    Scans every object under ``gs://<bucket>/<prefix>`` and compares the
    custom metadata value stored at :data:`_HASH_META_KEY`.

    Args:
        local_path: Path to the local file to check.
        bucket: GCS bucket name (without ``gs://`` prefix).
        prefix: Object-name prefix to scope the search.
        client: A ``google.cloud.storage.Client`` (or compatible mock).

    Returns:
        ``True`` if an object with a matching content hash is found.
    """
    content_hash = compute_content_hash(local_path)
    gcs_client = _get_client(client)
    bucket_obj = gcs_client.bucket(bucket)

    for blob in bucket_obj.list_blobs(prefix=prefix):
        blob_meta = blob.metadata or {}
        if blob_meta.get(_HASH_META_KEY) == content_hash:
            return True
    return False


def upload_to_gcs(
    local_path: str,
    bucket: str,
    prefix: str,
    *,
    skip_duplicates: bool = True,
    client: Any | None = None,
) -> dict[str, Any]:
    """Upload a single file to GCS with content-hash deduplication.

    The object name is constructed as ``<prefix>/<filename>``.  The file's
    SHA-256 hash is attached as custom metadata so future dedup checks are
    fast.

    Args:
        local_path: Local file to upload.
        bucket: Target GCS bucket name.
        prefix: Object-name prefix (acts like a directory).
        skip_duplicates: When ``True`` (default), skip the upload if a file
            with the same content hash already exists under *prefix*.
        client: A ``google.cloud.storage.Client`` or compatible mock.
            Defaults to a real client constructed with ``project="mmv-cloud"``.

    Returns:
        A dict with keys:

        - ``local_path`` — the original local path.
        - ``gcs_uri`` — the ``gs://`` URI of the (existing or new) object.
        - ``content_hash`` — SHA-256 hex digest.
        - ``was_duplicate`` — ``True`` if the upload was skipped.
        - ``uploaded_at`` — ISO-8601 timestamp (``None`` when skipped).
    """
    content_hash = compute_content_hash(local_path)
    filename = os.path.basename(local_path)
    # Normalise: strip trailing slash, then append filename.
    blob_name = f"{prefix.rstrip('/')}/{filename}"
    gcs_uri = f"gs://{bucket}/{blob_name}"

    gcs_client = _get_client(client)
    bucket_obj = gcs_client.bucket(bucket)

    # -- Dedup check --------------------------------------------------------
    if skip_duplicates:
        for existing_blob in bucket_obj.list_blobs(prefix=prefix):
            existing_meta = existing_blob.metadata or {}
            if existing_meta.get(_HASH_META_KEY) == content_hash:
                return {
                    "local_path": local_path,
                    "gcs_uri": f"gs://{bucket}/{existing_blob.name}",
                    "content_hash": content_hash,
                    "was_duplicate": True,
                    "uploaded_at": None,
                }

    # -- Upload -------------------------------------------------------------
    blob = bucket_obj.blob(blob_name)
    blob.metadata = {_HASH_META_KEY: content_hash}
    blob.upload_from_filename(local_path)

    uploaded_at = datetime.now(timezone.utc).isoformat()

    return {
        "local_path": local_path,
        "gcs_uri": gcs_uri,
        "content_hash": content_hash,
        "was_duplicate": False,
        "uploaded_at": uploaded_at,
    }


def upload_directory_to_gcs(
    local_dir: str,
    bucket: str,
    prefix: str,
    *,
    pattern: str = "*.json",
    client: Any | None = None,
) -> list[dict[str, Any]]:
    """Upload all files matching *pattern* from a local directory to GCS.

    Uses :func:`upload_to_gcs` for each file, inheriting dedup behaviour.

    Args:
        local_dir: Path to the local directory to scan.
        bucket: Target GCS bucket name.
        prefix: Object-name prefix for all uploaded files.
        pattern: Glob pattern to filter files (default ``*.json``).
        client: A ``google.cloud.storage.Client`` or compatible mock.

    Returns:
        A list of result dicts (one per file), in the same format as
        :func:`upload_to_gcs`.
    """
    local_dir_path = Path(local_dir)
    if not local_dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {local_dir}")

    results: list[dict[str, Any]] = []
    matched_files = sorted(local_dir_path.glob(pattern))

    gcs_client = _get_client(client)

    for file_path in matched_files:
        if file_path.is_file():
            result = upload_to_gcs(
                str(file_path),
                bucket,
                prefix,
                client=gcs_client,
            )
            results.append(result)

    return results


# ---------------------------------------------------------------------------
# CLI demo — exercises upload + dedup via the local mock
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import textwrap

    # Late import so the module itself has no hard dep on the mock.
    from gcs_local import MockClient

    SAMPLE_DIR = Path("/tmp/mmv_initial_fetch")
    BUCKET = DEFAULT_BUCKET
    PREFIX = "demo/initial_fetch"

    # -- 1. Create sample data if it doesn't exist --------------------------
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    samples = {
        "property_a.json": {"address": "123 Main St", "price": 450_000},
        "property_b.json": {"address": "456 Oak Ave", "price": 620_000},
        "property_c.json": {"address": "789 Pine Rd", "price": 380_000},
    }
    for name, payload in samples.items():
        path = SAMPLE_DIR / name
        if not path.exists():
            path.write_text(json.dumps(payload, indent=2))
    print("=== Sample files ===")
    for f in sorted(SAMPLE_DIR.glob("*.json")):
        print(f"  {f}  (hash: {compute_content_hash(str(f))[:12]}...)")

    # -- 2. First upload (all new) ------------------------------------------
    print("\n=== First upload (expect 0 duplicates) ===")
    client = MockClient()
    results = upload_directory_to_gcs(str(SAMPLE_DIR), BUCKET, PREFIX, client=client)
    for r in results:
        status = "DUPLICATE (skipped)" if r["was_duplicate"] else "UPLOADED"
        print(f"  [{status}] {r['gcs_uri']}  hash={r['content_hash'][:12]}...")

    # -- 3. Second upload (all duplicates) ----------------------------------
    print("\n=== Second upload (expect ALL duplicates) ===")
    results2 = upload_directory_to_gcs(str(SAMPLE_DIR), BUCKET, PREFIX, client=client)
    for r in results2:
        status = "DUPLICATE (skipped)" if r["was_duplicate"] else "UPLOADED"
        print(f"  [{status}] {r['gcs_uri']}  hash={r['content_hash'][:12]}...")

    # -- 4. Modify one file and re-upload -----------------------------------
    print("\n=== Modify property_a.json and re-upload (expect 1 new, 2 dupes) ===")
    modified = samples["property_a.json"].copy()
    modified["price"] = 475_000
    (SAMPLE_DIR / "property_a.json").write_text(json.dumps(modified, indent=2))

    results3 = upload_directory_to_gcs(str(SAMPLE_DIR), BUCKET, PREFIX, client=client)
    for r in results3:
        status = "DUPLICATE (skipped)" if r["was_duplicate"] else "UPLOADED"
        print(f"  [{status}] {r['gcs_uri']}  hash={r['content_hash'][:12]}...")

    # -- 5. Verify is_duplicate standalone ----------------------------------
    print("\n=== is_duplicate() check ===")
    for name in samples:
        dup = is_duplicate(str(SAMPLE_DIR / name), BUCKET, PREFIX, client=client)
        print(f"  {name}: duplicate={dup}")

    print("\nDone. All dedup checks passed.")
