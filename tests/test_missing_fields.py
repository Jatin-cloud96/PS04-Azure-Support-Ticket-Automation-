"""
Tests ensuring missing or unreadable fields trigger review and are never hallucinated.
"""

from decimal import Decimal
from pathlib import Path
from src.core.pipeline import InvoicePipelineService
from src.core.models import ReviewStatus, ExtractedInvoiceData, LineItem
from src.core.validator import validate_invoice


def test_missing_invoice_number_sample(sample_invoices_dir: Path, pipeline_service: InvoicePipelineService):
    """Verifies that an invoice missing an invoice number routes to review."""
    pdf_path = sample_invoices_dir / "INV-2026-004_MissingField_NovaServices.pdf"
    content = pdf_path.read_bytes()

    record = pipeline_service.process_invoice(content, pdf_path.name)

    assert record.review_status == ReviewStatus.REQUIRES_REVIEW
    assert record.invoice_data is not None
    assert record.invoice_data.invoice_number is None
    assert "invoice_number" in record.invoice_data.missing_fields
    assert any("invoice_number" in reason for reason in record.review_reasons)


def test_missing_supplier_name():
    """Verifies that omitting supplier_name causes review routing."""
    invoice = ExtractedInvoiceData(
        supplier_name=None,  # Missing
        invoice_number="INV-999",
        invoice_date="2026-03-01",
        line_items=[
            LineItem(description="Service", quantity=Decimal("1"), unit_price=Decimal("100.00"), total_amount=Decimal("100.00"))
        ],
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("10.00"),
        total=Decimal("110.00")
    )

    status, reasons, _ = validate_invoice(invoice)
    assert status == ReviewStatus.REQUIRES_REVIEW
    assert "supplier_name" in invoice.missing_fields


def test_empty_line_items():
    """Verifies that an invoice without line items fails validation."""
    invoice = ExtractedInvoiceData(
        supplier_name="Valid Supplier Ltd",
        invoice_number="INV-999",
        invoice_date="2026-03-01",
        line_items=[],  # Empty items
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("10.00"),
        total=Decimal("110.00")
    )

    status, reasons, _ = validate_invoice(invoice)
    assert status == ReviewStatus.REQUIRES_REVIEW
    assert "line_items" in invoice.missing_fields
