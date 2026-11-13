
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from traceforge.services import connect


ALLOWED_TRANSITIONS = {
    "OPEN": "CONTAINMENT",
    "CONTAINMENT": "INVESTIGATING",
    "INVESTIGATING": "IMPLEMENTED",
    "IMPLEMENTED": "VERIFIED",
    "VERIFIED": "CLOSED",
}


DATE_COLUMNS = {
    "IMPLEMENTED": "implemented_date",
    "VERIFIED": "verified_date",
    "CLOSED": "closed_date",
}


def get_capa(db_path: str | Path, capa_id: str) -> dict:
    db = connect(db_path)

    try:
        capa = db.execute(
            """
            SELECT *
            FROM corrective_actions
            WHERE capa_id = ?
            """,
            (capa_id,),
        ).fetchone()

        if capa is None:
            raise ValueError(f"CAPA not found: {capa_id}")

        events = db.execute(
            """
            SELECT event_id, from_state, to_state, event_date, notes
            FROM lifecycle_events
            WHERE entity_type = 'CAPA' AND entity_id = ?
            ORDER BY event_id
            """,
            (capa_id,),
        ).fetchall()

        return {
            "capa": dict(capa),
            "history": [dict(event) for event in events],
        }

    finally:
        db.close()


def transition_capa(
    db_path: str | Path,
    capa_id: str,
    new_status: str,
    notes: str,
    event_date: str | None = None,
) -> dict:
    new_status = new_status.strip().upper()
    notes = notes.strip()
    event_date = event_date or date.today().isoformat()

    if not notes:
        raise ValueError("Transition notes or evidence are required.")

    try:
        date.fromisoformat(event_date)
    except ValueError as exc:
        raise ValueError(
            "Event date must use YYYY-MM-DD format."
        ) from exc

    db = connect(db_path)

    try:
        db.execute("BEGIN IMMEDIATE")

        capa = db.execute(
            """
            SELECT *
            FROM corrective_actions
            WHERE capa_id = ?
            """,
            (capa_id,),
        ).fetchone()

        if capa is None:
            raise ValueError(f"CAPA not found: {capa_id}")

        current_status = capa["status"]
        expected_status = ALLOWED_TRANSITIONS.get(current_status)

        if expected_status != new_status:
            raise ValueError(
                f"Invalid transition: {current_status} -> {new_status}. "
                f"Expected next status: {expected_status or 'NONE'}."
            )

        if event_date < capa["opened_date"]:
            raise ValueError(
                "Event date cannot precede the CAPA opening date."
            )

        if new_status in DATE_COLUMNS:
            previous_dates = [
                capa["opened_date"],
                capa["implemented_date"],
                capa["verified_date"],
            ]

            previous_dates = [
                value for value in previous_dates if value
            ]

            if previous_dates and event_date < max(previous_dates):
                raise ValueError(
                    "Lifecycle dates must be chronological."
                )

        if new_status == "VERIFIED":
            if not capa["implemented_date"]:
                raise ValueError(
                    "CAPA must have an implementation date before verification."
                )

            evidence = db.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM capa_verification_evidence AS evidence
                    JOIN inspection_results AS inspection
                        ON inspection.inspection_id = evidence.inspection_id
                    JOIN defects AS defect
                        ON defect.defect_id = ?
                    JOIN production_orders AS original_order
                        ON original_order.order_id = defect.order_id
                    JOIN production_orders AS verification_order
                        ON verification_order.order_id = inspection.order_id
                    JOIN inspection_plans AS plan
                        ON plan.plan_id = inspection.plan_id
                    WHERE evidence.capa_id = ?
                      AND evidence.evidence_type = 'INSPECTION'
                      AND evidence.verification_result = 'PASS'
                      AND inspection.result = 'PASS'
                      AND verification_order.sku = original_order.sku
                      AND plan.sku = verification_order.sku
                      AND date(inspection.inspected_at) > date(?)
                      AND date(inspection.inspected_at) <= date(?)
                )
                """,
                (
                    capa["defect_id"],
                    capa_id,
                    capa["implemented_date"],
                    event_date,
                ),
            ).fetchone()[0]

            if not evidence:
                raise ValueError(
                    "CAPA cannot be verified without a passing, "
                    "post-implementation inspection for the same product."
                )

        updates = ["status = ?"]
        parameters = [new_status]

        date_column = DATE_COLUMNS.get(new_status)

        if date_column:
            updates.append(f"{date_column} = ?")
            parameters.append(event_date)

        parameters.append(capa_id)

        db.execute(
            f"""
            UPDATE corrective_actions
            SET {", ".join(updates)}
            WHERE capa_id = ?
            """,
            parameters,
        )

        db.execute(
            """
            INSERT INTO lifecycle_events
            (
                entity_type,
                entity_id,
                from_state,
                to_state,
                event_date,
                notes
            )
            VALUES ('CAPA', ?, ?, ?, ?, ?)
            """,
            (
                capa_id,
                current_status,
                new_status,
                event_date,
                notes,
            ),
        )

        db.commit()

        return get_capa(db_path, capa_id)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def record_verification_evidence(
    db_path: str | Path,
    capa_id: str,
    evidence_type: str,
    evidence_reference: str,
    verification_result: str,
    evidence_notes: str,
    recorded_by: str,
    process_step_id: str | None = None,
    inspection_id: str | None = None,
    specification_id: str | None = None,
    temperature: float | None = None,
    pressure: float | None = None,
    recorded_at: str | None = None,
) -> dict:
    evidence_type = evidence_type.strip().upper()
    verification_result = verification_result.strip().upper()
    evidence_reference = evidence_reference.strip()
    evidence_notes = evidence_notes.strip()
    recorded_by = recorded_by.strip()
    recorded_at = recorded_at or datetime.now().isoformat(
        timespec="seconds"
    )

    if evidence_type not in {
        "PROCESS_MEASUREMENT",
        "INSPECTION",
        "DOCUMENT",
        "OTHER",
    }:
        raise ValueError("Unsupported evidence type.")

    if verification_result not in {
        "PASS",
        "FAIL",
        "INCONCLUSIVE",
    }:
        raise ValueError("Invalid verification result.")

    if not all([
        evidence_reference,
        evidence_notes,
        recorded_by,
    ]):
        raise ValueError(
            "Evidence reference, notes, and recorder are required."
        )

    try:
        datetime.fromisoformat(recorded_at)
    except ValueError as exc:
        raise ValueError(
            "Recorded date must use a valid ISO date/time."
        ) from exc

    db = connect(db_path)

    try:
        db.execute("BEGIN IMMEDIATE")

        capa = db.execute(
            """
            SELECT
                ca.*,
                d.order_id,
                po.sku
            FROM corrective_actions AS ca
            JOIN defects AS d
                ON d.defect_id = ca.defect_id
            JOIN production_orders AS po
                ON po.order_id = d.order_id
            WHERE ca.capa_id = ?
            """,
            (capa_id,),
        ).fetchone()

        if capa is None:
            raise ValueError(f"CAPA not found: {capa_id}")

        if capa["status"] not in {
            "IMPLEMENTED",
            "VERIFIED",
        }:
            raise ValueError(
                "Verification evidence can only be recorded "
                "after implementation."
            )

        if not capa["implemented_date"]:
            raise ValueError(
                "CAPA must have an implementation date."
            )

        if db.execute(
            """
            SELECT 1
            FROM capa_verification_evidence
            WHERE capa_id = ?
              AND evidence_reference = ?
            """,
            (capa_id, evidence_reference),
        ).fetchone():
            raise ValueError(
                "This evidence reference already exists."
            )

        implementation_date = date.fromisoformat(
            capa["implemented_date"]
        )

        if evidence_type == "PROCESS_MEASUREMENT":
            if not process_step_id or not specification_id:
                raise ValueError(
                    "Process measurements require a process step "
                    "and approved specification."
                )

            step = db.execute(
                """
                SELECT
                    ps.*,
                    po.sku
                FROM process_steps AS ps
                JOIN production_orders AS po
                    ON po.order_id = ps.order_id
                WHERE ps.step_id = ?
                """,
                (process_step_id,),
            ).fetchone()

            spec = db.execute(
                """
                SELECT *
                FROM process_specifications
                WHERE specification_id = ?
                """,
                (specification_id,),
            ).fetchone()

            if step is None or spec is None:
                raise ValueError(
                    "Process step or specification not found."
                )

            if (
                step["sku"] != capa["sku"]
                or spec["sku"] != step["sku"]
                or spec["machine_id"] != step["machine_id"]
                or spec["process_name"] != step["process_name"]
            ):
                raise ValueError(
                    "Process step and specification do not match "
                    "the CAPA product and process context."
                )

            if not step["completed_at"]:
                raise ValueError(
                    "Process step must be completed."
                )

            if (
                not spec["approved_by"].strip()
                or not spec["approval_reference"].strip()
            ):
                raise ValueError(
                    "Process specification must have approval details."
                )

            step_date = date.fromisoformat(
                step["completed_at"][:10]
            )

            spec_start = date.fromisoformat(
                spec["effective_from"]
            )

            spec_end = (
                date.fromisoformat(spec["effective_to"])
                if spec["effective_to"]
                else None
            )

            if step_date < spec_start or (
                spec_end and step_date > spec_end
            ):
                raise ValueError(
                    "Specification was not effective "
                    "on the process date."
                )

            if step_date <= implementation_date:
                raise ValueError(
                    "Process evidence must be from after implementation."
                )

            temperature = step["temperature"]
            pressure = step["pressure"]

            checks = [
                (
                    temperature,
                    spec["temperature_min"],
                    spec["temperature_max"],
                ),
                (
                    pressure,
                    spec["pressure_min"],
                    spec["pressure_max"],
                ),
            ]

            for reading, minimum, maximum in checks:
                if minimum is not None or maximum is not None:
                    if reading is None:
                        raise ValueError(
                            "A required process measurement is missing."
                        )

                    if minimum is not None and reading < minimum:
                        raise ValueError(
                            "Process measurement is below specification."
                        )

                    if maximum is not None and reading > maximum:
                        raise ValueError(
                            "Process measurement is above specification."
                        )

            if verification_result != "PASS":
                raise ValueError(
                    "Process measurements within approved limits "
                    "must be recorded as PASS."
                )

        elif evidence_type == "INSPECTION":
            if not inspection_id:
                raise ValueError(
                    "Inspection evidence requires an inspection ID."
                )

            inspection = db.execute(
                """
                SELECT
                    inspection.*,
                    po.sku,
                    plan.sku AS plan_sku
                FROM inspection_results AS inspection
                JOIN production_orders AS po
                    ON po.order_id = inspection.order_id
                JOIN inspection_plans AS plan
                    ON plan.plan_id = inspection.plan_id
                WHERE inspection.inspection_id = ?
                """,
                (inspection_id,),
            ).fetchone()

            if inspection is None:
                raise ValueError(
                    "Inspection record not found."
                )

            if (
                inspection["sku"] != capa["sku"]
                or inspection["plan_sku"] != capa["sku"]
            ):
                raise ValueError(
                    "Inspection must belong to the same product as the CAPA."
                )

            inspection_date = date.fromisoformat(
                inspection["inspected_at"][:10]
            )

            if inspection_date <= implementation_date:
                raise ValueError(
                    "Verification inspection must occur "
                    "after implementation."
                )

            if inspection["result"] != verification_result:
                raise ValueError(
                    "Evidence result must match the inspection result."
                )

        cursor = db.execute(
            """
            INSERT INTO capa_verification_evidence (
                capa_id,
                evidence_type,
                process_step_id,
                inspection_id,
                specification_id,
                evidence_reference,
                temperature,
                pressure,
                verification_result,
                evidence_notes,
                recorded_by,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                capa_id,
                evidence_type,
                process_step_id,
                inspection_id,
                specification_id,
                evidence_reference,
                temperature,
                pressure,
                verification_result,
                evidence_notes,
                recorded_by,
                recorded_at,
            ),
        )

        db.commit()

        return {
            "evidence_id": cursor.lastrowid,
            "capa_id": capa_id,
            "evidence_type": evidence_type,
            "evidence_reference": evidence_reference,
            "verification_result": verification_result,
            "recorded_at": recorded_at,
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
