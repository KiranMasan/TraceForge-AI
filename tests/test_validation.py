import sqlite3
from pathlib import Path

from traceforge.validation import validate_database


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "src" / "traceforge" / "schema.sql"


def create_test_database(tmp_path, inspection_plan_sku):
    db_path = tmp_path / "validation_test.db"

    connection = sqlite3.connect(db_path)
    connection.executescript(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    connection.executemany(
        "INSERT INTO products (sku, name, category) VALUES (?, ?, ?)",
        [
            ("SKU-A", "Product A", "Electronics"),
            ("SKU-B", "Product B", "Electronics"),
        ],
    )

    connection.execute(
        """
        INSERT INTO production_orders
        (order_id, sku, planned_quantity, start_date, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("ORDER-001", "SKU-A", 10, "2026-01-01", "PLANNED"),
    )

    connection.execute(
        """
        INSERT INTO inspection_plans
        (plan_id, sku, inspection_stage, sample_size, effective_from)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("PLAN-001", inspection_plan_sku, "FINAL", 5, "2026-01-01"),
    )

    connection.execute(
        """
        INSERT INTO inspection_results
        (inspection_id, order_id, plan_id, inspected_at,
         inspected_quantity, defective_quantity, result)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "INSPECTION-001",
            "ORDER-001",
            "PLAN-001",
            "2026-01-02",
            5,
            0,
            "PASS",
        ),
    )

    connection.commit()
    connection.close()

    return db_path


def test_matching_inspection_plan_passes(tmp_path):
    db_path = create_test_database(tmp_path, "SKU-A")

    report = validate_database(db_path)

    assert report["valid"] is True
    assert report["error_count"] == 0


def test_inspection_plan_for_different_product_is_rejected(tmp_path):
    db_path = create_test_database(tmp_path, "SKU-B")

    report = validate_database(db_path)

    assert report["valid"] is False

    matching_errors = [
        error
        for error in report["errors"]
        if error["check"] == "inspection_plan_sku_consistency"
    ]

    assert len(matching_errors) == 1

    error = matching_errors[0]

    assert error["violations"] == 1
    assert error["examples"][0]["inspection_id"] == "INSPECTION-001"
    assert error["examples"][0]["order_sku"] == "SKU-A"
    assert error["examples"][0]["plan_sku"] == "SKU-B"
