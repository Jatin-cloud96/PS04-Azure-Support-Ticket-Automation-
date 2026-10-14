"""
Automated end-to-end local demonstration runner for the PS03 Invoice Processing Pipeline.
Demonstrates:
1. Azurite container initialization (invoices-input, invoices-output, invoices-review, invoices-failed, invoices-hashes)
2. Ingestion of 5 sample invoices (clean PDF, scanned PNG image, arithmetic mismatch, missing field, zero tax)
3. Processing and automated separation of VALID invoices from records requiring review
4. Re-upload / Deduplication scenario demonstrating idempotency
5. Field accuracy benchmarking against annotations.json
"""

import sys
import os
import time
import subprocess
import socket
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.azure_adapters.blob_service import (
    AzureBlobAdapter,
    CONTAINER_INPUT,
    CONTAINER_OUTPUT,
    CONTAINER_REVIEW,
    CONTAINER_FAILED,
    CONTAINER_HASHES
)
from src.core.pipeline import InvoicePipelineService
from src.core.models import ReviewStatus
from src.evaluation.evaluate_accuracy import evaluate_pipeline, print_evaluation_report


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks whether a local port is actively listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


def ensure_azurite_running():
    """Checks for running Azurite instance; starts one in background if necessary."""
    if is_port_in_use(10000):
        print("[Azurite] Azurite Blob Service is already active on port 10000.")
        return None

    print("[Azurite] Starting local Azurite emulator with --skipApiVersionCheck...")
    azurite_dir = PROJECT_ROOT / ".azurite"
    azurite_dir.mkdir(exist_ok=True)
    
    import shutil
    azurite_bin = shutil.which("azurite")
    if not azurite_bin and os.name == "nt":
        appdata_npm = Path(os.environ.get("APPDATA", "")) / "npm" / "azurite.cmd"
        if appdata_npm.exists():
            azurite_bin = str(appdata_npm)

    if not azurite_bin:
        azurite_bin = "azurite"

    cmd = [azurite_bin, "--silent", "--skipApiVersionCheck", "--location", str(azurite_dir), "--blobHost", "127.0.0.1", "--blobPort", "10000"]
    try:
        proc = subprocess.Popen(cmd, shell=(os.name == "nt"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(6):
            time.sleep(1)
            if is_port_in_use(10000):
                print("[Azurite] Azurite started successfully on port 10000.")
                return proc
    except Exception as ex:
        print(f"[Azurite launch notice] {ex}")
    
    print("[WARNING] Could not automatically launch Azurite process. Ensure 'azurite' is running.")
    return None


def run_full_demo():
    print("=" * 80)
    print("  PS03 AZURE INVOICE PROCESSING PIPELINE - LOCAL DEMONSTRATION")
    print("=" * 80)

    # 1. Start Azurite
    azurite_proc = ensure_azurite_running()

    # 2. Initialize Azure Storage Adapter
    print("\n[Step 1] Connecting to Azurite and initializing Blob Containers...")
    blob_adapter = AzureBlobAdapter()
    try:
        blob_adapter.initialize_containers()
        print(" -> Initialized containers: [invoices-input, invoices-output, invoices-review, invoices-failed, invoices-hashes]")
    except Exception as e:
        print(f"[Error connecting to Azurite] {e}")
        print("Please ensure Azurite is running: 'azurite' or 'scripts/start_azurite.ps1'")
        return

    # 3. Locate Sample Invoices
    sample_dir = PROJECT_ROOT / "sample_data" / "invoices"
    sample_files = sorted(list(sample_dir.glob("*.*")))
    if not sample_files:
        print(f"[Error] No sample invoices found in {sample_dir}. Generating samples...")
        from src.generators.generate_samples import generate_all_samples
        generate_all_samples(PROJECT_ROOT)
        sample_files = sorted(list(sample_dir.glob("*.*")))

    # 4. Ingestion into Azurite input container
    print("\n[Step 2] Uploading 5 Sample Invoices to 'invoices-input' container...")
    pipeline = InvoicePipelineService()

    for file_path in sample_files:
        content = file_path.read_bytes()
        blob_adapter.upload_blob(CONTAINER_INPUT, file_path.name, content)
        print(f" -> Uploaded to {CONTAINER_INPUT}/{file_path.name} ({len(content)} bytes)")

    # 5. Process Invoices (Trigger Simulation)
    print("\n[Step 3] Triggering Processing Pipeline across all ingested invoices...")
    print("-" * 80)
    print(f"{'File Name':<42} | {'Review Status':<16} | {'Target Container':<16} | {'Latency'}")
    print("-" * 80)

    for file_path in sample_files:
        content = blob_adapter.download_blob(CONTAINER_INPUT, file_path.name)
        record = pipeline.process_invoice(content, file_path.name)
        target_container, out_blob = blob_adapter.route_processed_record(record)
        
        status_str = record.review_status.value
        dur_str = f"{record.metadata.processing_duration_ms:.1f}ms"
        print(f"{file_path.name:<42} | {status_str:<16} | {target_container:<16} | {dur_str}")
        if record.review_reasons:
            for r in record.review_reasons:
                print(f"   [Discrepancy/Flag] {r}")

    # 6. Deduplication Scenario (Idempotency)
    print("\n[Step 4] Testing Deduplication / Idempotency Scenario...")
    duplicate_candidate = sample_files[0]
    print(f" -> Simulating repeated ingestion of: {duplicate_candidate.name}")
    dup_content = duplicate_candidate.read_bytes()
    
    # Process identical file
    dup_record = pipeline.process_invoice(dup_content, duplicate_candidate.name)
    print(f" -> Result Status: {dup_record.review_status.value}")
    print(f" -> Audit Message: {dup_record.review_reasons[0]}")
    assert dup_record.review_status == ReviewStatus.DUPLICATE_SKIPPED, "Deduplication check failed!"
    print(" -> SUCCESS: Pipeline prevented duplicate reprocessing and maintained idempotency.")

    # 7. Audit Container Contents
    print("\n[Step 5] Checking Container Outputs in Azurite...")
    output_blobs = blob_adapter.list_blobs(CONTAINER_OUTPUT)
    review_blobs = blob_adapter.list_blobs(CONTAINER_REVIEW)
    print(f" -> Invoices Output (VALID):   {output_blobs}")
    print(f" -> Invoices Review (FLAGGED): {review_blobs}")

    # 8. Benchmark Accuracy Evaluation
    print("\n[Step 6] Running Ground-Truth Accuracy Benchmark against annotations.json...")
    accuracy_report = evaluate_pipeline(PROJECT_ROOT)
    print_evaluation_report(accuracy_report)

    print("\n[SUCCESS] Local demonstration completed successfully!")


if __name__ == "__main__":
    run_full_demo()
