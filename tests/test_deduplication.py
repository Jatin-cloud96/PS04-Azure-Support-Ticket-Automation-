"""
Tests for SHA-256 content hashing, idempotency, and duplicate rejection.
"""

from pathlib import Path
from src.core.deduplication import compute_sha256, DeduplicationRegistry
from src.core.pipeline import InvoicePipelineService
from src.core.models import ReviewStatus


def test_compute_sha256_deterministic():
    """Verifies that hashing identical payloads generates identical SHA-256 hex strings."""
    data_a = b"Sample Invoice Binary Content 123"
    data_b = b"Sample Invoice Binary Content 123"
    assert compute_sha256(data_a) == compute_sha256(data_b)


def test_registry_prevents_duplicate_reprocessing():
    """Verifies that duplicate content hashes are flagged and rejected."""
    registry = DeduplicationRegistry()
    hash_val = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    first_attempt = registry.register(hash_val, "INV-001")
    assert first_attempt.is_duplicate is False

    second_attempt = registry.register(hash_val, "INV-001_copy")
    assert second_attempt.is_duplicate is True
    assert "Duplicate invoice detected" in second_attempt.message


def test_pipeline_deduplication_e2e(sample_invoices_dir: Path, pipeline_service: InvoicePipelineService):
    """Verifies end-to-end duplicate detection through pipeline service."""
    pdf_path = sample_invoices_dir / "INV-2026-001_AcmeCorp.pdf"
    content = pdf_path.read_bytes()

    # Ingest first time -> VALID
    first_record = pipeline_service.process_invoice(content, pdf_path.name)
    assert first_record.review_status == ReviewStatus.VALID

    # Ingest second time -> DUPLICATE_SKIPPED
    second_record = pipeline_service.process_invoice(content, "re_uploaded_" + pdf_path.name)
    assert second_record.review_status == ReviewStatus.DUPLICATE_SKIPPED
    assert "Duplicate invoice detected" in second_record.review_reasons[0]
