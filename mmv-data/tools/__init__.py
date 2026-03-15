"""MMV Data Tools — fetchers and utilities for external data sources.

All data fetching for the MMV platform lives here per domain-structure rules.
Each fetcher module wraps its responses with provenance metadata via tag_provenance().
"""

from .provenance import tag_provenance
from .gcs import (
    compute_content_hash,
    is_duplicate,
    upload_to_gcs,
    upload_directory_to_gcs,
)

__all__ = [
    "tag_provenance",
    "compute_content_hash",
    "is_duplicate",
    "upload_to_gcs",
    "upload_directory_to_gcs",
]
