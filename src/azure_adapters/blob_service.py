"""
Azure Blob Storage adapter supporting Azurite (local emulator) and Azure Cloud Storage.
Encapsulates container management, blob I/O, idempotency tracking, and output routing.
"""

from __future__ import annotations
import json
from typing import Optional, List, Dict, Any, Tuple
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

from src.core.models import ProcessedInvoiceRecord, ReviewStatus

DEFAULT_CONNECTION_STRING = "UseDevelopmentStorage=true"

CONTAINER_INPUT = "invoices-input"
CONTAINER_OUTPUT = "invoices-output"
CONTAINER_REVIEW = "invoices-review"
CONTAINER_FAILED = "invoices-failed"
CONTAINER_HASHES = "invoices-hashes"

ALL_CONTAINERS = [
    CONTAINER_INPUT,
    CONTAINER_OUTPUT,
    CONTAINER_REVIEW,
    CONTAINER_FAILED,
    CONTAINER_HASHES
]


class AzureBlobAdapter:
    """Wrapper for Azure Blob Storage operations with Azurite support."""

    def __init__(self, connection_string: Optional[str] = None):
        import os
        self.connection_string = connection_string or os.environ.get("AZURE_STORAGE_CONNECTION_STRING") or DEFAULT_CONNECTION_STRING
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

    def initialize_containers(self) -> None:
        """Creates required pipeline containers if they do not exist."""
        for container_name in ALL_CONTAINERS:
            try:
                self.blob_service_client.create_container(container_name)
            except ResourceExistsError:
                pass

    def upload_blob(
        self,
        container_name: str,
        blob_name: str,
        data: bytes | str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Uploads content to specified container."""
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        payload = data.encode("utf-8") if isinstance(data, str) else data
        blob_client.upload_blob(payload, overwrite=True, metadata=metadata)
        return blob_client.url

    def download_blob(self, container_name: str, blob_name: str) -> bytes:
        """Downloads blob bytes from container."""
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        return blob_client.download_blob().readall()

    def list_blobs(self, container_name: str) -> List[str]:
        """Lists blob names in specified container."""
        container_client = self.blob_service_client.get_container_client(container_name)
        return [b.name for b in container_client.list_blobs()]

    def is_hash_registered(self, content_hash: str) -> bool:
        """Checks if a content hash exists in the hashes container."""
        try:
            container_client = self.blob_service_client.get_container_client(CONTAINER_HASHES)
            blob_client = container_client.get_blob_client(f"{content_hash}.txt")
            return blob_client.exists()
        except Exception:
            return False

    def register_hash(self, content_hash: str, filename: str) -> None:
        """Registers a hash into the hashes container."""
        container_client = self.blob_service_client.get_container_client(CONTAINER_HASHES)
        blob_client = container_client.get_blob_client(f"{content_hash}.txt")
        blob_client.upload_blob(f"processed:{filename}".encode("utf-8"), overwrite=True)

    def route_processed_record(self, record: ProcessedInvoiceRecord) -> Tuple[str, str]:
        """
        Saves structured JSON output to the appropriate container based on ReviewStatus:
        - VALID -> invoices-output
        - REQUIRES_REVIEW -> invoices-review
        - FAILED or DUPLICATE_SKIPPED -> invoices-failed or review queue
        Returns (destination_container, output_blob_name).
        """
        base_name = record.metadata.source_blob_name.rsplit(".", 1)[0]
        output_blob_name = f"{base_name}_result.json"

        # Serialize Pydantic model with Decimals converted to float/string
        json_data = record.model_dump_json(indent=2)

        if record.review_status == ReviewStatus.VALID:
            target_container = CONTAINER_OUTPUT
        elif record.review_status == ReviewStatus.REQUIRES_REVIEW:
            target_container = CONTAINER_REVIEW
        else:
            target_container = CONTAINER_FAILED

        self.upload_blob(
            container_name=target_container,
            blob_name=output_blob_name,
            data=json_data,
            content_type="application/json",
            metadata={
                "review_status": record.review_status.value,
                "file_sha256": record.metadata.file_sha256,
                "invoice_id": record.invoice_id
            }
        )

        # Register hash if it was a processed document
        if record.review_status in (ReviewStatus.VALID, ReviewStatus.REQUIRES_REVIEW):
            self.register_hash(record.metadata.file_sha256, record.metadata.source_blob_name)

        return target_container, output_blob_name
