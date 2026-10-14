"""
Accuracy evaluation and benchmarking suite for the PS03 Invoice Processing Pipeline.
Evaluates extracted fields against ground-truth annotations.json.
Reports exact field match rates, arithmetic validation accuracy, and review routing metrics.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
from decimal import Decimal
from typing import Dict, Any, List

from src.core.pipeline import InvoicePipelineService
from src.core.models import ProcessedInvoiceRecord, ReviewStatus


def evaluate_pipeline(base_dir: Path) -> Dict[str, Any]:
    """Runs extraction over all benchmark samples and compares with ground truth."""
    annotations_path = base_dir / "sample_data" / "annotations.json"
    invoices_dir = base_dir / "sample_data" / "invoices"
    expected_out_dir = base_dir / "sample_data" / "expected_outputs"
    expected_out_dir.mkdir(parents=True, exist_ok=True)

    with open(annotations_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    pipeline = InvoicePipelineService()
    results: List[Dict[str, Any]] = []

    fields_to_check = [
        "supplier_name",
        "invoice_number",
        "invoice_date",
        "subtotal",
        "tax_amount",
        "total"
    ]

    total_field_checks = 0
    correct_field_checks = 0
    status_checks = 0
    correct_status_checks = 0

    for sample in ground_truth["samples"]:
        filename = sample["file_name"]
        file_path = invoices_dir / filename
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        record: ProcessedInvoiceRecord = pipeline.process_invoice(file_bytes, filename)

        # Save as expected output fixture
        out_file = expected_out_dir / f"{filename.rsplit('.', 1)[0]}_result.json"
        with open(out_file, "w", encoding="utf-8") as out_f:
            out_f.write(record.model_dump_json(indent=2))

        # Field comparisons
        exp_vals = sample["expected_values"]
        inv_data = record.invoice_data
        field_matches: Dict[str, bool] = {}

        if inv_data:
            # Supplier
            actual_supplier = inv_data.supplier_name
            exp_supplier = exp_vals["supplier_name"]
            supplier_match = actual_supplier == exp_supplier
            field_matches["supplier_name"] = supplier_match

            # Invoice number
            actual_inv_no = inv_data.invoice_number
            exp_inv_no = exp_vals["invoice_number"]
            inv_no_match = actual_inv_no == exp_inv_no
            field_matches["invoice_number"] = inv_no_match

            # Invoice Date
            actual_date = inv_data.invoice_date
            exp_date = exp_vals["invoice_date"]
            date_match = actual_date == exp_date
            field_matches["invoice_date"] = date_match

            # Subtotal
            actual_subtotal = f"{inv_data.subtotal:.2f}" if inv_data.subtotal is not None else None
            exp_subtotal = exp_vals["subtotal"]
            subtotal_match = actual_subtotal == exp_subtotal
            field_matches["subtotal"] = subtotal_match

            # Tax
            actual_tax = f"{inv_data.tax_amount:.2f}" if inv_data.tax_amount is not None else None
            exp_tax = exp_vals["tax_amount"]
            tax_match = actual_tax == exp_tax
            field_matches["tax_amount"] = tax_match

            # Total
            actual_total = f"{inv_data.total:.2f}" if inv_data.total is not None else None
            exp_total = exp_vals["total"]
            total_match = actual_total == exp_total
            field_matches["total"] = total_match

            for fld in fields_to_check:
                total_field_checks += 1
                if field_matches.get(fld, False):
                    correct_field_checks += 1

        # Check Review Status
        status_checks += 1
        expected_status = sample["expected_review_status"]
        actual_status = record.review_status.value
        status_match = actual_status == expected_status
        if status_match:
            correct_status_checks += 1

        results.append({
            "file_name": filename,
            "format": sample["format"],
            "expected_status": expected_status,
            "actual_status": actual_status,
            "status_match": status_match,
            "field_matches": field_matches,
            "duration_ms": record.metadata.processing_duration_ms,
            "review_reasons": record.review_reasons
        })

    field_accuracy = (correct_field_checks / total_field_checks) * 100.0 if total_field_checks else 0.0
    status_accuracy = (correct_status_checks / status_checks) * 100.0 if status_checks else 0.0

    return {
        "total_samples": len(ground_truth["samples"]),
        "total_field_checks": total_field_checks,
        "correct_field_checks": correct_field_checks,
        "field_accuracy_pct": round(field_accuracy, 2),
        "status_accuracy_pct": round(status_accuracy, 2),
        "details": results
    }


def print_evaluation_report(benchmark_results: Dict[str, Any]):
    """Renders a structured markdown report of the benchmark evaluation."""
    print("=" * 80)
    print("  PS03 INVOICE EXTRACTION & VALIDATION BENCHMARK EVALUATION REPORT")
    print("=" * 80)
    print(f"Total Samples Evaluated: {benchmark_results['total_samples']}")
    print(f"Total Field Assertions: {benchmark_results['total_field_checks']}")
    print(f"Field Accuracy:         {benchmark_results['field_accuracy_pct']}% ({benchmark_results['correct_field_checks']}/{benchmark_results['total_field_checks']})")
    print(f"Routing Status Accuracy:{benchmark_results['status_accuracy_pct']}%")
    print("-" * 80)
    print(f"{'File Name':<42} | {'Expected':<16} | {'Actual':<16} | {'Match'}")
    print("-" * 80)
    for row in benchmark_results["details"]:
        match_str = "[PASS]" if row["status_match"] else "[FAIL]"
        print(f"{row['file_name']:<42} | {row['expected_status']:<16} | {row['actual_status']:<16} | {match_str}")
        if row["review_reasons"]:
            for reason in row["review_reasons"]:
                print(f"   --> Reason: {reason}")
    print("=" * 80)


if __name__ == "__main__":
    report = evaluate_pipeline(Path(__file__).parent.parent.parent)
    print_evaluation_report(report)
