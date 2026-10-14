"""
Azure Functions v2 Python Programming Model entrypoint.
Triggered whenever an invoice document is uploaded to the 'invoices-input' container.
Executes deduplication, OCR/document extraction, arithmetic validation, and routes outputs.
"""

import logging
import azure.functions as func

from src.core.pipeline import InvoicePipelineService
from src.core.models import ReviewStatus
from src.azure_adapters.blob_service import (
    AzureBlobAdapter,
    CONTAINER_OUTPUT,
    CONTAINER_REVIEW,
    CONTAINER_FAILED,
    CONTAINER_HASHES
)

app = func.FunctionApp()
pipeline_service = InvoicePipelineService()
blob_adapter = AzureBlobAdapter()


@app.blob_trigger(
    arg_name="invoiceblob",
    path="invoices-input/{name}",
    connection="AzureWebJobsStorage"
)
def process_invoice_blob(invoiceblob: func.InputStream):
    """
    Blob Trigger function executed on invoice upload.
    Reads binary content, processes invoice, and persists structured JSON
    to either 'invoices-output' (VALID) or 'invoices-review' (REQUIRES_REVIEW).
    """
    blob_name = invoiceblob.name.split("/")[-1]
    logging.info(f"==> [Azure Function] Processing incoming invoice blob: {blob_name} ({invoiceblob.length} bytes)")

    try:
        content_bytes = invoiceblob.read()
        
        # Process invoice through decoupled core pipeline
        result_record = pipeline_service.process_invoice(
            document_bytes=content_bytes,
            filename=blob_name
        )

        # Route output to appropriate blob container
        target_container, output_blob = blob_adapter.route_processed_record(result_record)

        logging.info(
            f"==> [Azure Function] Completed {blob_name}: Status={result_record.review_status.value} "
            f"-> Destination={target_container}/{output_blob} "
            f"(Latency: {result_record.metadata.processing_duration_ms}ms)"
        )

        if result_record.review_reasons:
            for reason in result_record.review_reasons:
                logging.warning(f"   [Review Reason] {reason}")

    except Exception as exc:
        logging.error(f"[Azure Function Error] Failure processing blob {blob_name}: {str(exc)}", exc_info=True)
        # Log failure record to dead-letter / failure queue
        failure_payload = {
            "blob_name": blob_name,
            "error": str(exc),
            "status": ReviewStatus.FAILED.value
        }
        blob_adapter.upload_blob(
            container_name=CONTAINER_FAILED,
            blob_name=f"{blob_name}_failure.json",
            data=str(failure_payload),
            content_type="application/json"
        )
        raise exc
