"""
Azure Blob Storage adapter supporting Azurite (local emulator) and Azure Cloud Storage.
Encapsulates container management, blob I/O, idempotency tracking, and output routing.
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Tuple

from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
)
from azure.core.exceptions import ResourceExistsError

from src.core.models import ProcessedInvoiceRecord, ReviewStatus


DEFAULT_CONNECTION_STRING = "UseDevelopmentStorage=true"

# Pin the API version instead of using the SDK's default.
AZURE_STORAGE_API_VERSION = "2023-11-03"

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
    CONTAINER_HASHES,
]


class AzureBlobAdapter:
    """Wrapper for Azure Blob Storage operations with Azurite support."""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = (
            connection_string
            or os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
            or DEFAULT_CONNECTION_STRING
        )

        self.blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string,
            api_version=AZURE_STORAGE_API_VERSION,
        )

    def initialize_containers(self) -> None:
        """Create required pipeline containers if they do not exist."""
        for container_name in ALL_CONTAINERS:
            try:
                self.blob_service_client.create_container(container_name)
            except ResourceExistsError:
                # The container already exists.
                pass

    def upload_blob(
        self,
        container_name: str,
        blob_name: str,
        data: bytes | str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload content to the specified container."""
        container_client = self.blob_service_client.get_container_client(
            container_name
        )
        blob_client = container_client.get_blob_client(blob_name)

        payload = data.encode("utf-8") if isinstance(data, str) else data

        blob_client.upload_blob(
            payload,
            overwrite=True,
            metadata=metadata,
            content_settings=ContentSettings(content_type=content_type),
        )

        return blob_client.url

    def download_blob(self, container_name: str, blob_name: str) -> bytes:
        """Download blob bytes from a container."""
        container_client = self.blob_service_client.get_container_client(
            container_name
        )
        blob_client = container_client.get_blob_client(blob_name)

        return blob_client.download_blob().readall()

    def list_blobs(self, container_name: str) -> List[str]:
        """Return the names of blobs in a container."""
        container_client = self.blob_service_client.get_container_client(
            container_name
        )

        return [blob.name for blob in container_client.list_blobs()]

    def is_hash_registered(self, content_hash: str) -> bool:
        """Check whether a content hash exists in the hashes container."""
        try:
            container_client = self.blob_service_client.get_container_client(
                CONTAINER_HASHES
            )
            blob_client = container_client.get_blob_client(
                f"{content_hash}.txt"
            )

            return blob_client.exists()

        except Exception:
            return False

    def register_hash(self, content_hash: str, filename: str) -> None:
        """Register a content hash to prevent duplicate processing."""
        container_client = self.blob_service_client.get_container_client(
            CONTAINER_HASHES
        )
        blob_client = container_client.get_blob_client(
            f"{content_hash}.txt"
        )

        blob_client.upload_blob(
            f"processed:{filename}".encode("utf-8"),
            overwrite=True,
            content_settings=ContentSettings(
                content_type="text/plain"
            ),
        )

    def route_processed_record(
        self,
        record: ProcessedInvoiceRecord,
    ) -> Tuple[str, str]:
        """
        Save structured JSON output to the appropriate container.

        VALID -> invoices-output
        REQUIRES_REVIEW -> invoices-review
        FAILED or DUPLICATE_SKIPPED -> invoices-failed

        Returns:
            A tuple containing the destination container and blob name.
        """
        base_name = record.metadata.source_blob_name.rsplit(".", 1)[0]
        output_blob_name = f"{base_name}_result.json"

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
                "invoice_id": str(record.invoice_id),
            },
        )

        # Register hashes for processed documents.
        if record.review_status in (
            ReviewStatus.VALID,
            ReviewStatus.REQUIRES_REVIEW,
        ):
            self.register_hash(
                record.metadata.file_sha256,
                record.metadata.source_blob_name,
            )

        return target_container, output_blob_name
