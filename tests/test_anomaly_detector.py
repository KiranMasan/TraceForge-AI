
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from traceforge.anomaly_detector import (
    detect_case,
    evaluate_detections,
    run_detection,
)


DATA_DIR = PROJECT_ROOT / "data" / "generated" / "starter"
GROUND_TRUTH = (
    PROJECT_ROOT
    / "data"
    / "ground_truth"
    / "starter_ground_truth.json"
)


def test_all_synthetic_anomalies_are_detected():
    report = run_detection(
        DATA_DIR / "traceforge.db",
        DATA_DIR / "anomaly_cases.json",
        GROUND_TRUTH,
    )

    metrics = report["metrics"]

    assert metrics["evaluated_cases"] == 5
    assert metrics["true_positives"] == 5
    assert metrics["false_positives"] == 0
    assert metrics["false_negatives"] == 0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0


def test_all_expected_anomaly_types_are_present():
    cases = json.loads(
        (DATA_DIR / "anomaly_cases.json").read_text(
            encoding="utf-8"
        )
    )

    expected = {
        "NONEXISTENT_LOT_REFERENCE",
        "BOM_MATERIAL_NOT_CONSUMED",
        "CAPA_CLOSED_BEFORE_VERIFICATION",
        "DEFECTS_EXCEED_INSPECTED_QUANTITY",
        "BROKEN_TRACEABILITY",
    }

    actual = {case["type"] for case in cases}

    assert actual == expected


def test_metrics_calculation():
    detections = [
        {
            "case_id": "A",
            "detected": True,
            "detected_type": "BROKEN_TRACEABILITY",
        },
        {
            "case_id": "B",
            "detected": False,
            "detected_type": None,
        },
    ]

    ground_truth = {
        "A": {
            "is_anomaly": True,
            "expected_type": "BROKEN_TRACEABILITY",
        },
        "B": {
            "is_anomaly": False,
            "expected_type": None,
        },
    }

    metrics = evaluate_detections(detections, ground_truth)

    assert metrics["true_positives"] == 1
    assert metrics["true_negatives"] == 1
    assert metrics["false_positives"] == 0
    assert metrics["false_negatives"] == 0
    assert metrics["f1_score"] == 1.0
