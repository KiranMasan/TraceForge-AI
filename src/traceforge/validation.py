
from __future__ import annotations

import sqlite3
from pathlib import Path


def validate_database(db_path: str | Path) -> dict:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    errors = []
    counts = {}

    def check(name: str, sql: str, message: str) -> None:
        rows = connection.execute(sql).fetchall()
        if rows:
            errors.append({
                "check": name,
                "message": message,
                "violations": len(rows),
                "examples": [dict(row) for row in rows[:5]],
            })

    tables = [
        "suppliers", "products", "bom", "material_lots", "machines",
        "production_orders", "material_consumption", "process_steps",
        "inspection_plans", "inspection_results", "defects",
        "corrective_actions", "lifecycle_events",
    ]

    for table in tables:
        counts[table] = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        errors.append({
            "check": "database_integrity",
            "message": integrity,
            "violations": 1,
        })

    foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_keys:
        errors.append({
            "check": "foreign_keys",
            "message": "Foreign-key violations found",
            "violations": len(foreign_keys),
            "examples": [tuple(row) for row in foreign_keys[:5]],
        })

    check(
        "material_balance",
        """SELECT lot_id, quantity_received, quantity_consumed
           FROM material_lots
           WHERE quantity_consumed > quantity_received
              OR quantity_consumed < 0""",
        "Material lot consumption is outside its received quantity.",
    )

    check(
        "consumption_material_match",
        """SELECT mc.consumption_id
           FROM material_consumption mc
           JOIN material_lots ml ON ml.lot_id = mc.lot_id
           WHERE mc.material_code != ml.material_code""",
        "A consumption record references a lot of a different material.",
    )

    check(
        "consumption_order_sku_bom",
        """SELECT po.order_id, b.material_code
           FROM production_orders po
           JOIN bom b ON b.sku = po.sku
           LEFT JOIN material_consumption mc
             ON mc.order_id = po.order_id
            AND mc.material_code = b.material_code
           WHERE b.effective_from <= po.start_date
             AND (b.effective_to IS NULL OR b.effective_to >= po.start_date)
             AND mc.consumption_id IS NULL""",
        "A production order is missing a required BOM material consumption.",
    )

    check(
        "inspection_arithmetic",
        """SELECT inspection_id, inspected_quantity, defective_quantity
           FROM inspection_results
           WHERE defective_quantity < 0
              OR defective_quantity > inspected_quantity""",
        "Defective quantity must be between zero and inspected quantity.",
    )

    check(
        "inspection_result_consistency",
        """SELECT inspection_id, result, defective_quantity
           FROM inspection_results
           WHERE (result = 'PASS' AND defective_quantity != 0)
              OR (result = 'FAIL' AND defective_quantity = 0)""",
        "Inspection result does not match its defective quantity.",
    )

    check(
        "defect_quantity_reconciliation",
        """SELECT ir.inspection_id, ir.defective_quantity,
                  COALESCE(SUM(d.affected_quantity), 0) AS defect_total
           FROM inspection_results ir
           LEFT JOIN defects d ON d.inspection_id = ir.inspection_id
           GROUP BY ir.inspection_id
           HAVING defect_total != ir.defective_quantity""",
        "Defect quantities do not reconcile with inspection results.",
    )

    check(
        "defect_order_consistency",
        """SELECT d.defect_id
           FROM defects d
           JOIN inspection_results ir ON ir.inspection_id = d.inspection_id
           WHERE d.order_id != ir.order_id""",
        "A defect's production order differs from its inspection order.",
    )

    check(
        "defect_step_consistency",
        """SELECT d.defect_id
           FROM defects d
           JOIN process_steps ps ON ps.step_id = d.step_id
           WHERE ps.order_id != d.order_id""",
        "A defect references a process step from another order.",
    )

    check(
        "defect_lot_traceability",
        """SELECT d.defect_id
           FROM defects d
           WHERE d.lot_id IS NOT NULL
             AND NOT EXISTS (
                 SELECT 1 FROM material_consumption mc
                 WHERE mc.order_id = d.order_id
                   AND mc.lot_id = d.lot_id
             )""",
        "A defect references a material lot not consumed by its order.",
    )

    check(
        "capa_closed_without_verification",
        """SELECT capa_id
           FROM corrective_actions
           WHERE status = 'CLOSED'
             AND (verified_date IS NULL OR closed_date IS NULL)""",
        "A corrective action cannot close before verification.",
    )

    check(
        "capa_date_order",
        """SELECT capa_id
           FROM corrective_actions
           WHERE (implemented_date IS NOT NULL
                  AND implemented_date < opened_date)
              OR (verified_date IS NOT NULL
                  AND (implemented_date IS NULL
                       OR verified_date < implemented_date))
              OR (closed_date IS NOT NULL
                  AND (verified_date IS NULL
                       OR closed_date < verified_date))""",
        "Corrective-action lifecycle dates are inconsistent.",
    )

    check(
        "duplicate_primary_business_ids",
        """SELECT order_id, COUNT(*) AS n
           FROM production_orders
           GROUP BY order_id
           HAVING COUNT(*) > 1""",
        "Duplicate production order identifiers found.",
    )

    connection.close()

    return {
        "valid": len(errors) == 0,
        "counts": counts,
        "error_count": len(errors),
        "errors": errors,
    }
