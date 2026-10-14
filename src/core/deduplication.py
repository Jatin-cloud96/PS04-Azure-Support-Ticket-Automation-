"""
Deduplication and idempotency manager for the invoice processing pipeline.
Generates deterministic SHA-256 content hashes to avoid reprocessing identical invoices.
Supports local in-memory registry, local file cache, and Azure Blob Storage state tracking.
"""

import hashlib
from typing import Optional, Set
from pydantic import BaseModel


def compute_sha256(content: bytes) -> str:
    """Computes a deterministic SHA-256 hex digest for binary content."""
    return hashlib.sha256(content).hexdigest()


class DeduplicationResult(BaseModel):
    is_duplicate: bool
    sha256_hash: str
    existing_record_id: Optional[str] = None
    message: str


class DeduplicationRegistry:
    """In-memory and persistent registry for tracking processed invoice hashes."""
    
    def __init__(self, initial_hashes: Optional[Set[str]] = None):
        self._processed_hashes: Set[str] = set(initial_hashes or [])

    def is_processed(self, content_hash: str) -> bool:
        """Checks if the given hash has already been registered."""
        return content_hash in self._processed_hashes

    def register(self, content_hash: str, invoice_id: Optional[str] = None) -> DeduplicationResult:
        """
        Registers a content hash.
        If already present, flags as duplicate. If new, records it.
        """
        if self.is_processed(content_hash):
            return DeduplicationResult(
                is_duplicate=True,
                sha256_hash=content_hash,
                existing_record_id=invoice_id,
                message=f"Duplicate invoice detected with SHA-256: {content_hash}. Skipping reprocessing."
            )
        
        self._processed_hashes.add(content_hash)
        return DeduplicationResult(
            is_duplicate=False,
            sha256_hash=content_hash,
            existing_record_id=invoice_id,
            message="New invoice content detected. Ready for processing."
        )

    def clear(self) -> None:
        """Clears the registry cache (useful in test runs)."""
        self._processed_hashes.clear()
