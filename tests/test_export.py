"""
Tests for CSV and JSON accounting export endpoints.
Verifies RFC 4180 compliance, header alignment, and status filtering.
"""

import csv
import io
import json
import pytest
from fastapi.testclient import TestClient
from src.ui.app import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def seed_processed_invoices():
    """Process all sample invoices into Azurite so the export tests don't depend on test order."""
    response = client.post("/api/run-pipeline")
    assert response.status_code == 200, response.text


def test_export_csv_all_records():
    """Verifies that the full CSV export returns all records with valid headers."""
    response = client.get("/api/export/csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=" in response.headers.get("content-disposition", "")

    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)

    # Verify Header
    header = rows[0]
    expected_columns = [
        "Invoice ID",
        "Source File",
        "Review Status",
        "Target Container",
        "Supplier Name",
        "Supplier Address",
        "Invoice Number",
        "Invoice Date",
        "Subtotal",
        "Tax Amount",
        "Grand Total",
        "Line Items Count",
        "Arithmetic Valid",
        "Review Reasons",
        "SHA256 Hash",
        "Processing Latency (ms)",
        "Processed Timestamp UTC"
    ]
    assert header == expected_columns

    # Verify at least 5 invoice rows exist
    data_rows = rows[1:]
    assert len(data_rows) >= 5

    # Check that known suppliers appear
    suppliers = [r[4] for r in data_rows]
    assert "Acme Industrial Supplies Ltd" in suppliers
    assert "Apex Logistics & Freight Corp" in suppliers
    assert "Vertex Cloud Solutions Inc" in suppliers


def test_export_csv_filtered_valid_only():
    """Verifies that filtering by status=VALID only returns approved valid invoices."""
    response = client.get("/api/export/csv?status=VALID")
    assert response.status_code == 200

    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    data_rows = rows[1:]

    assert len(data_rows) >= 3

    # All rows must have review status VALID
    for row in data_rows:
        assert row[2] == "VALID"

    # Arithmetic mismatch invoice should be excluded
    source_files = [r[1] for r in data_rows]
    assert "INV-2026-003_ArithmeticMismatch_VertexTech.pdf" not in source_files
    assert "INV-2026-001_AcmeCorp.pdf" in source_files


def test_export_json_ledger():
    """Verifies that JSON export returns a valid structured array."""
    response = client.get("/api/export/json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    assert any(inv.get("review_status") == "VALID" for inv in data)
