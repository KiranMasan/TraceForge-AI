
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def detect_case(connection: sqlite3.Connection, case: dict) -> dict:
    case_id = case["case_id"]
    anomaly_type = case["type"]
    record = case["record"]
    reason = None

    if anomaly_type == "NONEXISTENT_LOT_REFERENCE":
        exists = connection.execute(
            "SELECT 1 FROM material_lots WHERE lot_id = ?",
            (record.get("lot_id"),),
        ).fetchone()

        if not exists:
            reason = "Referenced material lot does not exist."

    elif anomaly_type == "BOM_MATERIAL_NOT_CONSUMED":
        required_materials = record.get("required_materials")
        consumed_materials = record.get("consumed_materials")

        if required_materials is not None and consumed_materials is not None:
            missing = set(required_materials) - set(consumed_materials)

            if missing:
                reason = (
                    "Required BOM materials were not consumed: "
                    + ", ".join(sorted(missing))
                )
        else:
            order_id = record.get("order_id")
            material = record.get("bom_material")

            order = connection.execute(
                """
                SELECT sku, start_date
                FROM production_orders
                WHERE order_id = ?
                """,
                (order_id,),
            ).fetchone()

            if not order:
                reason = "Production order does not exist."
            else:
                required = connection.execute(
                    """
                    SELECT 1
                    FROM bom
                    WHERE sku = ?
                      AND material_code = ?
                      AND effective_from <= ?
                      AND (effective_to IS NULL OR effective_to >= ?)
                    """,
                    (
                        order["sku"],
                        material,
                        order["start_date"],
                        order["start_date"],
                    ),
                ).fetchone()

                consumed = connection.execute(
                    """
                    SELECT 1
                    FROM material_consumption
                    WHERE order_id = ?
                      AND material_code = ?
                    """,
                    (order_id, material),
                ).fetchone()

                if required and not consumed:
                    reason = (
                        f"Required BOM material {material} was not consumed."
                    )
                elif not required:
                    reason = (
                        f"Material {material} is not part of the effective BOM."
                    )

    elif anomaly_type == "CAPA_CLOSED_BEFORE_VERIFICATION":
        if (
            record.get("status") == "CLOSED"
            and (
                not record.get("verified_date")
                or not record.get("closed_date")
                or record["closed_date"] < record["verified_date"]
            )
        ):
            reason = "CAPA is closed without valid prior verification."

    elif anomaly_type == "DEFECTS_EXCEED_INSPECTED_QUANTITY":
        inspected = record.get("inspected_quantity", 0)
        defective = record.get("defective_quantity", 0)

        if defective < 0 or inspected <= 0 or defective > inspected:
            reason = (
                "Defective quantity is outside the inspected quantity."
            )

    elif anomaly_type == "BROKEN_TRACEABILITY":
        missing = [
            field
            for field in ("order_id", "lot_id", "step_id")
            if not record.get(field)
        ]

        if missing:
            reason = (
                "Defect traceability links are missing: "
                + ", ".join(missing)
            )

    else:
        reason = f"Unsupported anomaly type: {anomaly_type}"

    return {
        "case_id": case_id,
        "detected": reason is not None,
        "detected_type": anomaly_type if reason else None,
        "reason": reason,
    }


def evaluate_detections(detections, ground_truth):
    tp = fp = fn = tn = 0
    type_matches = 0
    positive_count = 0

    for detection in detections:
        case_id = detection["case_id"]
        truth = ground_truth.get(case_id)

        if truth is None:
            continue

        actual = bool(truth["is_anomaly"])
        predicted = bool(detection["detected"])

        if actual and predicted:
            tp += 1
            positive_count += 1

            if detection["detected_type"] == truth["expected_type"]:
                type_matches += 1

        elif predicted and not actual:
            fp += 1

        elif actual and not predicted:
            fn += 1
            positive_count += 1

        else:
            tn += 1

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0
    )

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "detected_type_accuracy": (
            round(type_matches / positive_count, 4)
            if positive_count
            else 0
        ),
        "evaluated_cases": tp + fp + fn + tn,
    }


def run_detection(db_path, anomaly_path, ground_truth_path):
    # Ground truth is deliberately not passed to the detector.
    cases = json.loads(
        Path(anomaly_path).read_text(encoding="utf-8")
    )

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row

    try:
        detections = [
            detect_case(connection, case)
            for case in cases
        ]
    finally:
        connection.close()

    # Load ground truth only after predictions have been generated.
    ground_truth = json.loads(
        Path(ground_truth_path).read_text(encoding="utf-8")
    )

    metrics = evaluate_detections(detections, ground_truth)

    return {
        "detector": "TraceForge rule-based anomaly detector",
        "detections": detections,
        "metrics": metrics,
    }
