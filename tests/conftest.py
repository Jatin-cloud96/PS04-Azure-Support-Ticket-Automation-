"""
Pytest configuration and reusable fixtures for the PS03 test suite.
Automatically starts Azurite emulator for integration tests if not already active.
"""

import sys
import os
import time
import socket
import shutil
import subprocess
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.pipeline import InvoicePipelineService
from src.core.deduplication import DeduplicationRegistry
from src.azure_adapters.blob_service import AzureBlobAdapter


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


@pytest.fixture(scope="session", autouse=True)
def azurite_session():
    """Session-level fixture ensuring Azurite is running for storage tests."""
    proc = None
    if not is_port_in_use(10000):
        azurite_dir = PROJECT_ROOT / ".azurite"
        azurite_dir.mkdir(exist_ok=True)

        azurite_bin = shutil.which("azurite")
        if not azurite_bin and os.name == "nt":
            appdata_npm = Path(os.environ.get("APPDATA", "")) / "npm" / "azurite.cmd"
            if appdata_npm.exists():
                azurite_bin = str(appdata_npm)

        if not azurite_bin:
            azurite_bin = "azurite"

        cmd = [
            azurite_bin,
            "--silent",
            "--skipApiVersionCheck",
            "--location",
            str(azurite_dir),
            "--blobHost",
            "127.0.0.1",
            "--blobPort",
            "10000"
        ]
        try:
            proc = subprocess.Popen(cmd, shell=(os.name == "nt"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(6):
                time.sleep(1)
                if is_port_in_use(10000):
                    break
        except Exception:
            pass

    yield proc

    if proc is not None:
        try:
            proc.terminate()
            proc.kill()
        except Exception:
            pass


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def sample_invoices_dir(project_root: Path) -> Path:
    return project_root / "sample_data" / "invoices"


@pytest.fixture
def annotations_file(project_root: Path) -> Path:
    return project_root / "sample_data" / "annotations.json"


@pytest.fixture
def clean_registry() -> DeduplicationRegistry:
    return DeduplicationRegistry()


@pytest.fixture
def pipeline_service(clean_registry: DeduplicationRegistry) -> InvoicePipelineService:
    return InvoicePipelineService(deduplication_registry=clean_registry)
