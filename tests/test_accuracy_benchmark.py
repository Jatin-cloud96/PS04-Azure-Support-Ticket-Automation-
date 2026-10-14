"""
Regression tests verifying accuracy benchmark scores against annotations.json.
"""

from pathlib import Path
from src.evaluation.evaluate_accuracy import evaluate_pipeline


def test_full_benchmark_accuracy(project_root: Path):
    """Asserts that pipeline achieves >= 95% field accuracy and 100% status routing."""
    report = evaluate_pipeline(project_root)

    assert report["total_samples"] == 5
    assert report["field_accuracy_pct"] >= 95.0, f"Expected >= 95% field accuracy, got {report['field_accuracy_pct']}%"
    assert report["status_accuracy_pct"] == 100.0, f"Expected 100% status accuracy, got {report['status_accuracy_pct']}%"
