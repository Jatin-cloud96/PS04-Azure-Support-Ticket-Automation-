"""
Domain models for the PS03 Azure Invoice Processing Pipeline.
Includes strongly-typed schemas for line items, raw extraction evidence,
arithmetic validation results, review routing statuses, and pipeline outcomes.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ReviewStatus(str, Enum):
    """Status indicating how an invoice should be routed post-processing."""
    VALID = "VALID"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    DUPLICATE_SKIPPED = "DUPLICATE_SKIPPED"
    FAILED = "FAILED"


class ExtractionFieldEvidence(BaseModel):
    """Audit evidence tracing where and how a field was extracted."""
    field_name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence score from 0.0 to 1.0")
    source_page: int = 1
    text_snippet: Optional[str] = None
    bounding_box: Optional[Dict[str, float]] = None


class LineItem(BaseModel):
    """An individual line item within an invoice."""
    description: str
    quantity: Decimal = Field(default=Decimal("1.00"))
    unit_price: Decimal = Field(ge=Decimal("0.00"))
    total_amount: Decimal = Field(ge=Decimal("0.00"))

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ArithmeticValidationResult(BaseModel):
    """Arithmetic verification summary and discrepancies."""
    is_valid: bool
    calculated_subtotal: Decimal
    stated_subtotal: Optional[Decimal]
    calculated_tax: Optional[Decimal]
    stated_tax: Optional[Decimal]
    calculated_total: Decimal
    stated_total: Optional[Decimal]
    line_item_math_valid: bool = True
    subtotal_tax_sum_valid: bool = True
    rounding_method: str = "ROUND_HALF_UP (2 decimal places, tolerance +/- 0.01)"
    errors: List[str] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ExtractedInvoiceData(BaseModel):
    """Normalized structured invoice data extracted from document."""
    supplier_name: Optional[str] = None
    supplier_address: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    line_items: List[LineItem] = Field(default_factory=list)
    subtotal: Optional[Decimal] = None
    tax_rate_percent: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total: Optional[Decimal] = None
    
    # Auditability & completeness
    missing_fields: List[str] = Field(default_factory=list)
    uncertain_fields: List[str] = Field(default_factory=list)
    field_evidence: Dict[str, ExtractionFieldEvidence] = Field(default_factory=dict)
    raw_text: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ProcessingMetadata(BaseModel):
    """Operational metadata regarding the processing event."""
    source_blob_name: str
    file_sha256: str
    file_size_bytes: int
    content_type: str
    processed_timestamp_utc: str
    extractor_engine: str
    processing_duration_ms: float
    retry_count: int = 0


class ProcessedInvoiceRecord(BaseModel):
    """Complete structured output payload written to blob storage."""
    invoice_id: str
    review_status: ReviewStatus
    review_reasons: List[str] = Field(default_factory=list)
    invoice_data: Optional[ExtractedInvoiceData] = None
    arithmetic_validation: Optional[ArithmeticValidationResult] = None
    metadata: ProcessingMetadata

    model_config = ConfigDict(arbitrary_types_allowed=True)
