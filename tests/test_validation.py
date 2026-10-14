"""
Tests for arithmetic validation rules, rounding edge cases, and discrepancy logging.
"""

from decimal import Decimal
from pathlib import Path
from src.core.pipeline import InvoicePipelineService
from src.core.models import ReviewStatus, ExtractedInvoiceData, LineItem
from src.core.validator import validate_invoice, quantize_money


def test_arithmetic_mismatch_invoice(sample_invoices_dir: Path, pipeline_service: InvoicePipelineService):
    """Verifies that an invoice with a line-item to subtotal mismatch is routed to REQUIRES_REVIEW."""
    pdf_path = sample_invoices_dir / "INV-2026-003_ArithmeticMismatch_VertexTech.pdf"
    content = pdf_path.read_bytes()

    record = pipeline_service.process_invoice(content, pdf_path.name)

    assert record.review_status == ReviewStatus.REQUIRES_REVIEW
    assert record.arithmetic_validation is not None
    assert record.arithmetic_validation.is_valid is False
    assert record.arithmetic_validation.calculated_subtotal == Decimal("700.00")
    assert record.arithmetic_validation.stated_subtotal == Decimal("750.00")
    assert any("Subtotal mismatch" in reason for reason in record.review_reasons)


def test_rounding_half_up_tolerance():
    """Verifies that decimal quantizing uses ROUND_HALF_UP and respects +/- 0.01 tolerance."""
    assert quantize_money(Decimal("10.005")) == Decimal("10.01")
    assert quantize_money(Decimal("10.004")) == Decimal("10.00")

    # Valid invoice with fractional penny splits
    invoice = ExtractedInvoiceData(
        supplier_name="Rounding Test Corp",
        invoice_number="INV-RND-001",
        invoice_date="2026-03-01",
        line_items=[
            LineItem(description="Item 1", quantity=Decimal("3"), unit_price=Decimal("33.33"), total_amount=Decimal("99.99")),
            LineItem(description="Item 2", quantity=Decimal("1"), unit_price=Decimal("50.01"), total_amount=Decimal("50.01"))
        ],
        subtotal=Decimal("150.00"),
        tax_amount=Decimal("0.00"),
        total=Decimal("150.00")
    )

    status, reasons, arith_res = validate_invoice(invoice)
    assert status == ReviewStatus.VALID
    assert arith_res.is_valid is True
    assert len(reasons) == 0


def test_grand_total_mismatch():
    """Verifies that discrepancy between subtotal + tax and total triggers review."""
    invoice = ExtractedInvoiceData(
        supplier_name="Math Error Corp",
        invoice_number="INV-ERR-001",
        invoice_date="2026-03-01",
        line_items=[
            LineItem(description="Item 1", quantity=Decimal("1"), unit_price=Decimal("100.00"), total_amount=Decimal("100.00"))
        ],
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("10.00"),
        total=Decimal("125.00")  # Should be 110.00
    )

    status, reasons, arith_res = validate_invoice(invoice)
    assert status == ReviewStatus.REQUIRES_REVIEW
    assert arith_res.is_valid is False
    assert any("Grand total mismatch" in r for r in reasons)
