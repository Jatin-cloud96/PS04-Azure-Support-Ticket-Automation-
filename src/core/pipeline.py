"""
Core invoice processing pipeline orchestrator.
Coordinates deduplication, document extraction, arithmetic validation,
and status assignment into a unified, testable service.
"""

from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Optional, Tuple
from decimal import Decimal

from src.core.models import (
    ProcessedInvoiceRecord,
    ReviewStatus,
    ProcessingMetadata,
    ExtractedInvoiceData,
    ArithmeticValidationResult
)
from src.core.deduplication import compute_sha256, DeduplicationRegistry
from src.core.extractor import HybridDocumentExtractor
from src.core.validator import validate_invoice


class InvoicePipelineService:
    """
    Decoupled business logic service for end-to-end invoice automation.
    Can be executed standalone, inside Azure Functions, or in test harnesses.
    """

    def __init__(self, deduplication_registry: Optional[DeduplicationRegistry] = None):
        self.registry = deduplication_registry or DeduplicationRegistry()
        self.extractor = HybridDocumentExtractor()

    def process_invoice(
        self,
        document_bytes: bytes,
        filename: str,
        content_type: str = "application/pdf"
    ) -> ProcessedInvoiceRecord:
        """
        Executes the full pipeline for an invoice file:
        1. SHA-256 calculation & idempotency deduplication check
        2. Text and field extraction with audit evidence
        3. Arithmetic and completeness validation
        4. Review status determination
        5. Compilation of structured JSON record
        """
        start_time = time.perf_counter()
        utc_timestamp = datetime.now(timezone.utc).isoformat()
        file_sha256 = compute_sha256(document_bytes)
        file_size = len(document_bytes)

        # 1. Deduplication / Idempotency Check
        dedup_result = self.registry.register(file_sha256, invoice_id=filename)
        if dedup_result.is_duplicate:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ProcessedInvoiceRecord(
                invoice_id=filename,
                review_status=ReviewStatus.DUPLICATE_SKIPPED,
                review_reasons=[dedup_result.message],
                invoice_data=None,
                arithmetic_validation=None,
                metadata=ProcessingMetadata(
                    source_blob_name=filename,
                    file_sha256=file_sha256,
                    file_size_bytes=file_size,
                    content_type=content_type,
                    processed_timestamp_utc=utc_timestamp,
                    extractor_engine="DeduplicationFilter",
                    processing_duration_ms=round(duration_ms, 2)
                )
            )

        # 2. Document Extraction
        try:
            extracted_data, engine_name = self.extractor.extract(document_bytes, filename)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ProcessedInvoiceRecord(
                invoice_id=filename,
                review_status=ReviewStatus.FAILED,
                review_reasons=[f"Document extraction error: {str(exc)}"],
                invoice_data=None,
                arithmetic_validation=None,
                metadata=ProcessingMetadata(
                    source_blob_name=filename,
                    file_sha256=file_sha256,
                    file_size_bytes=file_size,
                    content_type=content_type,
                    processed_timestamp_utc=utc_timestamp,
                    extractor_engine="ErrorFallback",
                    processing_duration_ms=round(duration_ms, 2)
                )
            )

        # 3. Arithmetic & Completeness Validation
        review_status, review_reasons, arithmetic_result = validate_invoice(extracted_data)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        invoice_id_display = extracted_data.invoice_number or filename

        return ProcessedInvoiceRecord(
            invoice_id=invoice_id_display,
            review_status=review_status,
            review_reasons=review_reasons,
            invoice_data=extracted_data,
            arithmetic_validation=arithmetic_result,
            metadata=ProcessingMetadata(
                source_blob_name=filename,
                file_sha256=file_sha256,
                file_size_bytes=file_size,
                content_type=content_type,
                processed_timestamp_utc=utc_timestamp,
                extractor_engine=engine_name,
                processing_duration_ms=round(duration_ms, 2)
            )
        )
