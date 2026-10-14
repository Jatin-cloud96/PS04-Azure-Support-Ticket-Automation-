"""
Arithmetic and completeness validator for invoice records.
Implements documented rounding rules (ROUND_HALF_UP, 2 decimal places, +/- 0.01 tolerance)
and separates VALID invoices from those that REQUIRE_REVIEW.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple
from src.core.models import (
    ExtractedInvoiceData,
    ArithmeticValidationResult,
    ReviewStatus,
    LineItem
)

# Mandatory fields required for a valid invoice
MANDATORY_FIELDS = [
    "supplier_name",
    "invoice_number",
    "invoice_date",
    "line_items",
    "subtotal",
    "total"
]

TWO_PLACES = Decimal("0.01")
TOLERANCE = Decimal("0.01")


def quantize_money(amount: Decimal) -> Decimal:
    """Quantize decimal to 2 decimal places using standard ROUND_HALF_UP rounding."""
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def validate_invoice(
    invoice: ExtractedInvoiceData,
    min_confidence_threshold: float = 0.70
) -> Tuple[ReviewStatus, List[str], ArithmeticValidationResult]:
    """
    Validates an invoice for arithmetic correctness, field completeness, and confidence.
    
    Returns:
        review_status: ReviewStatus (VALID or REQUIRES_REVIEW)
        review_reasons: List of human-readable issues if review is needed
        arithmetic_result: ArithmeticValidationResult details
    """
    review_reasons: List[str] = []
    arithmetic_errors: List[str] = []

    # 1. Missing Fields Check
    missing_fields: List[str] = []
    for field_name in MANDATORY_FIELDS:
        val = getattr(invoice, field_name, None)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing_fields.append(field_name)
        elif field_name == "line_items" and (not isinstance(val, list) or len(val) == 0):
            missing_fields.append(field_name)

    invoice.missing_fields = missing_fields
    if missing_fields:
        review_reasons.append(f"Missing mandatory field(s): {', '.join(missing_fields)}")

    # 2. Confidence / Uncertain Fields Check
    uncertain_fields: List[str] = []
    for f_name, evidence in invoice.field_evidence.items():
        if evidence.confidence < min_confidence_threshold:
            uncertain_fields.append(f"{f_name} (confidence: {evidence.confidence:.2f})")
    invoice.uncertain_fields = uncertain_fields
    if uncertain_fields:
        review_reasons.append(f"Low confidence field(s): {', '.join(uncertain_fields)}")

    # 3. Arithmetic Validation
    # Calculate sum of line items
    calculated_subtotal = Decimal("0.00")
    line_item_math_valid = True

    for idx, item in enumerate(invoice.line_items, start=1):
        expected_line_total = quantize_money(item.quantity * item.unit_price)
        stated_line_total = quantize_money(item.total_amount)
        if abs(expected_line_total - stated_line_total) > TOLERANCE:
            err = (
                f"Line item #{idx} ('{item.description}') math discrepancy: "
                f"quantity ({item.quantity}) * unit_price ({item.unit_price}) = {expected_line_total}, "
                f"but stated total is {stated_line_total}."
            )
            arithmetic_errors.append(err)
            line_item_math_valid = False
        calculated_subtotal += stated_line_total

    calculated_subtotal = quantize_money(calculated_subtotal)

    # Subtotal validation against stated subtotal
    stated_subtotal = quantize_money(invoice.subtotal) if invoice.subtotal is not None else None
    if stated_subtotal is not None:
        if abs(calculated_subtotal - stated_subtotal) > TOLERANCE:
            err = (
                f"Subtotal mismatch: sum of line items is {calculated_subtotal}, "
                f"but stated subtotal is {stated_subtotal} (difference: {stated_subtotal - calculated_subtotal})."
            )
            arithmetic_errors.append(err)

    # Tax calculation
    stated_tax = quantize_money(invoice.tax_amount) if invoice.tax_amount is not None else Decimal("0.00")
    calculated_tax = stated_tax
    if invoice.tax_rate_percent is not None and stated_subtotal is not None:
        expected_tax = quantize_money(stated_subtotal * (invoice.tax_rate_percent / Decimal("100.00")))
        calculated_tax = expected_tax
        if abs(expected_tax - stated_tax) > TOLERANCE:
            err = (
                f"Tax amount mismatch: calculated tax at {invoice.tax_rate_percent}% "
                f"on {stated_subtotal} is {expected_tax}, but stated tax is {stated_tax}."
            )
            arithmetic_errors.append(err)

    # Grand Total validation
    base_subtotal = stated_subtotal if stated_subtotal is not None else calculated_subtotal
    calculated_total = quantize_money(base_subtotal + stated_tax)
    stated_total = quantize_money(invoice.total) if invoice.total is not None else None

    subtotal_tax_sum_valid = True
    if stated_total is not None:
        if abs(calculated_total - stated_total) > TOLERANCE:
            err = (
                f"Grand total mismatch: subtotal ({base_subtotal}) + tax ({stated_tax}) = {calculated_total}, "
                f"but stated total is {stated_total} (difference: {stated_total - calculated_total})."
            )
            arithmetic_errors.append(err)
            subtotal_tax_sum_valid = False

    is_arithmetic_valid = len(arithmetic_errors) == 0

    if not is_arithmetic_valid:
        review_reasons.extend(arithmetic_errors)

    arithmetic_result = ArithmeticValidationResult(
        is_valid=is_arithmetic_valid,
        calculated_subtotal=calculated_subtotal,
        stated_subtotal=stated_subtotal,
        calculated_tax=calculated_tax,
        stated_tax=stated_tax,
        calculated_total=calculated_total,
        stated_total=stated_total,
        line_item_math_valid=line_item_math_valid,
        subtotal_tax_sum_valid=subtotal_tax_sum_valid,
        errors=arithmetic_errors
    )

    # 4. Status Assignment
    if missing_fields or not is_arithmetic_valid or uncertain_fields:
        review_status = ReviewStatus.REQUIRES_REVIEW
    else:
        review_status = ReviewStatus.VALID

    return review_status, review_reasons, arithmetic_result
