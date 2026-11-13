
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

SCHEMA_PATH = PROJECT_ROOT / "src" / "traceforge" / "schema.sql"
MIGRATION_PATH = (
    PROJECT_ROOT
    / "src"
    / "traceforge"
    / "migrations"
    / "010_process_verification.sql"
)

from traceforge.capa_service import (
    get_capa,
    transition_capa,
    record_verification_evidence,
)


def create_capa_test_database(tmp_path):
    db_path = tmp_path / "capa_test.db"
    connection = sqlite3.connect(db_path)

    connection.executescript(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )
    connection.executescript(
        MIGRATION_PATH.read_text(encoding="utf-8")
    )

    connection.execute(
        """
        INSERT INTO products (sku, name, category)
        VALUES (?, ?, ?)
        """,
        ("SKU-TEST", "Test Product", "Electronics"),
    )

    connection.execute(
        """
        INSERT INTO production_orders
        (order_id, sku, planned_quantity, start_date, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("ORDER-TEST", "SKU-TEST", 100, "2026-01-01", "COMPLETED"),
    )

    connection.execute(
        """
        INSERT INTO inspection_plans
        (plan_id, sku, inspection_stage, sample_size, effective_from)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("PLAN-TEST", "SKU-TEST", "FINAL", 10, "2026-01-01"),
    )

    connection.execute(
        """
        INSERT INTO inspection_results
        (inspection_id, order_id, plan_id, inspected_at,
         inspected_quantity, defective_quantity, result)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "INSPECTION-TEST",
            "ORDER-TEST",
            "PLAN-TEST",
            "2026-01-02",
            10,
            1,
            "FAIL",
        ),
    )

    connection.execute(
        """
        INSERT INTO defects
        (defect_id, inspection_id, order_id, step_id, lot_id,
         defect_type, severity, affected_quantity, disposition)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "DEFECT-TEST",
            "INSPECTION-TEST",
            "ORDER-TEST",
            None,
            None,
            "ASSEMBLY",
            "HIGH",
            1,
            "REWORK",
        ),
    )

    connection.execute(
        """
        INSERT INTO corrective_actions
        (capa_id, defect_id, title, root_cause, status,
         opened_date, implemented_date, verified_date, closed_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "CAPA-TEST",
            "DEFECT-TEST",
            "Investigate test defect",
            "Initial investigation pending",
            "OPEN",
            "2026-01-03",
            None,
            None,
            None,
        ),
    )

    connection.execute(
        """
        INSERT INTO lifecycle_events
        (entity_type, entity_id, from_state, to_state, event_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "CAPA",
            "CAPA-TEST",
            None,
            "OPEN",
            "2026-01-03",
            "Initial CAPA creation",
        ),
    )

    connection.commit()
    connection.close()

    return db_path


def add_passing_verification_evidence(db_path):
    connection = sqlite3.connect(db_path)

    connection.execute(
        """
        INSERT INTO inspection_results
        (inspection_id, order_id, plan_id, inspected_at,
         inspected_quantity, defective_quantity, result)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "INSPECTION-VERIFICATION",
            "ORDER-TEST",
            "PLAN-TEST",
            "2026-01-07",
            10,
            0,
            "PASS",
        ),
    )

    connection.execute(
        """
        INSERT INTO capa_verification_evidence
        (capa_id, evidence_type, inspection_id, evidence_reference,
         verification_result, evidence_notes, recorded_by, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "CAPA-TEST",
            "INSPECTION",
            "INSPECTION-VERIFICATION",
            "TEST-VERIFICATION-001",
            "PASS",
            "Post-implementation inspection passed.",
            "test_user",
            "2026-01-07",
        ),
    )

    connection.commit()
    connection.close()


def test_complete_capa_lifecycle(tmp_path):
    db_path = create_capa_test_database(tmp_path)
    add_passing_verification_evidence(db_path)

    transitions = [
        ("CONTAINMENT", "Containment action recorded", "2026-01-04"),
        ("INVESTIGATING", "Root cause investigation", "2026-01-05"),
        ("IMPLEMENTED", "Corrective action implemented", "2026-01-06"),
        ("VERIFIED", "Verification successful", "2026-01-07"),
        ("CLOSED", "CAPA closure approved", "2026-01-08"),
    ]

    for status, notes, event_date in transitions:
        result = transition_capa(
            db_path, "CAPA-TEST", status, notes, event_date
        )

    capa = result["capa"]

    assert capa["status"] == "CLOSED"
    assert capa["implemented_date"] == "2026-01-06"
    assert capa["verified_date"] == "2026-01-07"
    assert capa["closed_date"] == "2026-01-08"
    assert len(result["history"]) == 6

    assert [
        event["to_state"] for event in result["history"]
    ] == [
        "OPEN",
        "CONTAINMENT",
        "INVESTIGATING",
        "IMPLEMENTED",
        "VERIFIED",
        "CLOSED",
    ]


def test_invalid_transition_is_rejected(tmp_path):
    db_path = create_capa_test_database(tmp_path)

    with pytest.raises(ValueError, match="Invalid transition"):
        transition_capa(
            db_path,
            "CAPA-TEST",
            "CLOSED",
            "Attempt to close without verification",
            "2026-01-04",
        )

    result = get_capa(db_path, "CAPA-TEST")
    assert result["capa"]["status"] == "OPEN"
    assert len(result["history"]) == 1


def test_transition_requires_notes(tmp_path):
    db_path = create_capa_test_database(tmp_path)

    with pytest.raises(ValueError, match="notes or evidence"):
        transition_capa(
            db_path,
            "CAPA-TEST",
            "CONTAINMENT",
            "   ",
            "2026-01-04",
        )

    result = get_capa(db_path, "CAPA-TEST")
    assert result["capa"]["status"] == "OPEN"
    assert len(result["history"]) == 1


def test_lifecycle_dates_must_be_chronological(tmp_path):
    db_path = create_capa_test_database(tmp_path)

    transition_capa(
        db_path, "CAPA-TEST", "CONTAINMENT",
        "Containment recorded", "2026-01-04"
    )
    transition_capa(
        db_path, "CAPA-TEST", "INVESTIGATING",
        "Investigation started", "2026-01-05"
    )
    transition_capa(
        db_path, "CAPA-TEST", "IMPLEMENTED",
        "Corrective action implemented", "2026-01-06"
    )

    with pytest.raises(ValueError, match="chronological"):
        transition_capa(
            db_path,
            "CAPA-TEST",
            "VERIFIED",
            "Verification attempted too early",
            "2026-01-05",
        )

    result = get_capa(db_path, "CAPA-TEST")
    assert result["capa"]["status"] == "IMPLEMENTED"
    assert result["capa"]["verified_date"] is None
    assert len(result["history"]) == 4


def test_verification_requires_passing_evidence(tmp_path):
    db_path = create_capa_test_database(tmp_path)

    transition_capa(
        db_path, "CAPA-TEST", "CONTAINMENT",
        "Containment recorded", "2026-01-04"
    )
    transition_capa(
        db_path, "CAPA-TEST", "INVESTIGATING",
        "Investigation started", "2026-01-05"
    )
    transition_capa(
        db_path, "CAPA-TEST", "IMPLEMENTED",
        "Corrective action implemented", "2026-01-06"
    )

    with pytest.raises(ValueError, match="passing"):
        transition_capa(
            db_path,
            "CAPA-TEST",
            "VERIFIED",
            "Attempt verification without evidence",
            "2026-01-07",
        )

    result = get_capa(db_path, "CAPA-TEST")
    assert result["capa"]["status"] == "IMPLEMENTED"
    assert result["capa"]["verified_date"] is None
    assert len(result["history"]) == 4


def test_record_passing_inspection_evidence(tmp_path):
    db_path = create_capa_test_database(tmp_path)

    transition_capa(
        db_path, "CAPA-TEST", "CONTAINMENT",
        "Containment recorded", "2026-01-04"
    )
    transition_capa(
        db_path, "CAPA-TEST", "INVESTIGATING",
        "Investigation started", "2026-01-05"
    )
    transition_capa(
        db_path, "CAPA-TEST", "IMPLEMENTED",
        "Corrective action implemented", "2026-01-06"
    )

    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        INSERT INTO inspection_results
        (inspection_id, order_id, plan_id, inspected_at,
         inspected_quantity, defective_quantity, result)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "INSPECTION-NEW",
            "ORDER-TEST",
            "PLAN-TEST",
            "2026-01-07",
            10,
            0,
            "PASS",
        ),
    )
    connection.commit()
    connection.close()

    result = record_verification_evidence(
        db_path=db_path,
        capa_id="CAPA-TEST",
        evidence_type="INSPECTION",
        inspection_id="INSPECTION-NEW",
        evidence_reference="TEST-NEW-001",
        verification_result="PASS",
        evidence_notes="Post-implementation inspection passed.",
        recorded_by="test_user",
        recorded_at="2026-01-07T10:00:00",
    )

    assert result["capa_id"] == "CAPA-TEST"
    assert result["verification_result"] == "PASS"

    connection = sqlite3.connect(db_path)
    row = connection.execute(
        """
        SELECT evidence_reference, inspection_id, verification_result
        FROM capa_verification_evidence
        WHERE capa_id = ?
        """,
        ("CAPA-TEST",),
    ).fetchone()
    connection.close()

    assert row == ("TEST-NEW-001", "INSPECTION-NEW", "PASS")


def test_accept_inspection_from_later_order_same_sku(tmp_path):
    db_path = create_capa_test_database(tmp_path)

    transition_capa(
        db_path, "CAPA-TEST", "CONTAINMENT",
        "Containment recorded", "2026-01-04"
    )
    transition_capa(
        db_path, "CAPA-TEST", "INVESTIGATING",
        "Investigation started", "2026-01-05"
    )
    transition_capa(
        db_path, "CAPA-TEST", "IMPLEMENTED",
        "Corrective action implemented", "2026-01-06"
    )

    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        INSERT INTO production_orders
        (order_id, sku, planned_quantity, start_date, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("ORDER-LATER", "SKU-TEST", 100, "2026-01-07", "COMPLETED"),
    )
    connection.execute(
        """
        INSERT INTO inspection_results
        (inspection_id, order_id, plan_id, inspected_at,
         inspected_quantity, defective_quantity, result)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "INSPECTION-LATER",
            "ORDER-LATER",
            "PLAN-TEST",
            "2026-01-07",
            10,
            0,
            "PASS",
        ),
    )
    connection.commit()
    connection.close()

    result = record_verification_evidence(
        db_path=db_path,
        capa_id="CAPA-TEST",
        evidence_type="INSPECTION",
        inspection_id="INSPECTION-LATER",
        evidence_reference="TEST-LATER-001",
        verification_result="PASS",
        evidence_notes="Passing inspection from a later production order.",
        recorded_by="test_user",
        recorded_at="2026-01-07T10:00:00",
    )

    assert result["verification_result"] == "PASS"
    assert result["capa_id"] == "CAPA-TEST"


def test_reject_inspection_from_different_sku(tmp_path):
    db_path = create_capa_test_database(tmp_path)

    transition_capa(
        db_path, "CAPA-TEST", "CONTAINMENT",
        "Containment recorded", "2026-01-04"
    )
    transition_capa(
        db_path, "CAPA-TEST", "INVESTIGATING",
        "Investigation started", "2026-01-05"
    )
    transition_capa(
        db_path, "CAPA-TEST", "IMPLEMENTED",
        "Corrective action implemented", "2026-01-06"
    )

    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        INSERT INTO production_orders
        (order_id, sku, planned_quantity, start_date, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("ORDER-OTHER", "SKU-OTHER", 100, "2026-01-07", "COMPLETED"),
    )
    connection.execute(
        """
        INSERT INTO inspection_results
        (inspection_id, order_id, plan_id, inspected_at,
         inspected_quantity, defective_quantity, result)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "INSPECTION-OTHER",
            "ORDER-OTHER",
            "PLAN-TEST",
            "2026-01-07",
            10,
            0,
            "PASS",
        ),
    )
    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="same product"):
        record_verification_evidence(
            db_path=db_path,
            capa_id="CAPA-TEST",
            evidence_type="INSPECTION",
            inspection_id="INSPECTION-OTHER",
            evidence_reference="TEST-OTHER-001",
            verification_result="PASS",
            evidence_notes="Inspection from a different product.",
            recorded_by="test_user",
            recorded_at="2026-01-07T10:00:00",
        )


def test_reject_duplicate_evidence_reference(tmp_path):
    db_path = create_capa_test_database(tmp_path)

    transition_capa(
        db_path, "CAPA-TEST", "CONTAINMENT",
        "Containment recorded", "2026-01-04"
    )
    transition_capa(
        db_path, "CAPA-TEST", "INVESTIGATING",
        "Investigation started", "2026-01-05"
    )
    transition_capa(
        db_path, "CAPA-TEST", "IMPLEMENTED",
        "Corrective action implemented", "2026-01-06"
    )

    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        INSERT INTO inspection_results
        (inspection_id, order_id, plan_id, inspected_at,
         inspected_quantity, defective_quantity, result)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "INSPECTION-DUPLICATE",
            "ORDER-TEST",
            "PLAN-TEST",
            "2026-01-07",
            10,
            0,
            "PASS",
        ),
    )
    connection.commit()
    connection.close()

    arguments = {
        "db_path": db_path,
        "capa_id": "CAPA-TEST",
        "evidence_type": "INSPECTION",
        "inspection_id": "INSPECTION-DUPLICATE",
        "evidence_reference": "DUPLICATE-REF-001",
        "verification_result": "PASS",
        "evidence_notes": "Passing verification inspection.",
        "recorded_by": "test_user",
        "recorded_at": "2026-01-07T10:00:00",
    }

    record_verification_evidence(**arguments)

    with pytest.raises(ValueError, match="already exists"):
        record_verification_evidence(**arguments)
