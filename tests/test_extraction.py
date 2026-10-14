"""
Tests for document extraction across digital PDFs, scanned images, and malformed inputs.
"""

from decimal import Decimal
from pathlib import Path
from src.core.pipeline import InvoicePipelineService
from src.core.models import ReviewStatus


def test_digital_pdf_extraction(sample_invoices_dir: Path, pipeline_service: InvoicePipelineService):
    """Verifies that all structured fields are extracted accurately from digital PDF."""
    pdf_path = sample_invoices_dir / "INV-2026-001_AcmeCorp.pdf"
    content = pdf_path.read_bytes()

    record = pipeline_service.process_invoice(content, pdf_path.name)

    assert record.review_status == ReviewStatus.VALID
    assert record.invoice_data is not None
    assert record.invoice_data.supplier_name == "Acme Industrial Supplies Ltd"
    assert record.invoice_data.invoice_number == "INV-2026-001"
    assert record.invoice_data.invoice_date == "2026-03-15"
    assert len(record.invoice_data.line_items) == 3
    assert record.invoice_data.subtotal == Decimal("1100.00")
    assert record.invoice_data.tax_amount == Decimal("110.00")
    assert record.invoice_data.total == Decimal("1210.00")
    assert "invoice_number" in record.invoice_data.field_evidence
    assert record.invoice_data.field_evidence["invoice_number"].confidence >= 0.90


def test_scanned_image_ocr_extraction(sample_invoices_dir: Path, pipeline_service: InvoicePipelineService):
    """Verifies OCR extraction on scanned image invoices."""
    png_path = sample_invoices_dir / "INV-2026-002_Scanned_ApexLogistics.png"
    content = png_path.read_bytes()

    record = pipeline_service.process_invoice(content, png_path.name, content_type="image/png")

    assert record.review_status == ReviewStatus.VALID
    assert record.invoice_data is not None
    assert record.invoice_data.supplier_name == "Apex Logistics & Freight Corp"
    assert record.invoice_data.invoice_number == "INV-2026-002"
    assert record.invoice_data.invoice_date == "2026-03-18"
    assert len(record.invoice_data.line_items) == 2
    assert record.invoice_data.subtotal == Decimal("900.00")
    assert record.invoice_data.tax_amount == Decimal("162.00")
    assert record.invoice_data.total == Decimal("1062.00")


def test_corrupted_file_handling(pipeline_service: InvoicePipelineService):
    """Verifies that corrupted bytes do not crash the pipeline and yield FAILED or review status."""
    corrupted_bytes = b"NOT_A_VALID_PDF_HEADER_CORRUPTED_STREAM_12345"
    record = pipeline_service.process_invoice(corrupted_bytes, "corrupted_invoice.pdf")

    assert record.review_status in (ReviewStatus.FAILED, ReviewStatus.REQUIRES_REVIEW)
    assert len(record.review_reasons) > 0
