"""
Tests for Azure Blob Storage integration, container routing, and persistence.
"""

from pathlib import Path
from src.azure_adapters.blob_service import (
    AzureBlobAdapter,
    CONTAINER_INPUT,
    CONTAINER_OUTPUT,
    CONTAINER_REVIEW,
    CONTAINER_FAILED
)
from src.core.pipeline import InvoicePipelineService
from src.core.models import ReviewStatus


def test_azure_blob_routing(sample_invoices_dir: Path, pipeline_service: InvoicePipelineService):
    """Verifies that AzureBlobAdapter accurately persists records to target containers."""
    blob_adapter = AzureBlobAdapter()
    blob_adapter.initialize_containers()

    # Process a valid invoice
    valid_pdf = sample_invoices_dir / "INV-2026-001_AcmeCorp.pdf"
    valid_record = pipeline_service.process_invoice(valid_pdf.read_bytes(), valid_pdf.name)
    target_c, out_blob = blob_adapter.route_processed_record(valid_record)

    assert target_c == CONTAINER_OUTPUT
    assert out_blob.endswith(".json")
    
    # Download written JSON from Azurite
    saved_bytes = blob_adapter.download_blob(target_c, out_blob)
    assert b"Acme Industrial Supplies Ltd" in saved_bytes
    assert b'"review_status": "VALID"' in saved_bytes

    # Process an arithmetic mismatch invoice
    mismatch_pdf = sample_invoices_dir / "INV-2026-003_ArithmeticMismatch_VertexTech.pdf"
    mismatch_record = pipeline_service.process_invoice(mismatch_pdf.read_bytes(), mismatch_pdf.name)
    target_review_c, review_out_blob = blob_adapter.route_processed_record(mismatch_record)

    assert target_review_c == CONTAINER_REVIEW
    saved_review_bytes = blob_adapter.download_blob(target_review_c, review_out_blob)
    assert b"Subtotal mismatch" in saved_review_bytes
    assert b'"review_status": "REQUIRES_REVIEW"' in saved_review_bytes
