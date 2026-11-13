
from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def trace_defect(db_path: str | Path, defect_id: str) -> dict:
    """Trace one defect backwards to its supplier and forwards to its CAPA."""

    db = connect(db_path)

    defect = db.execute(
        """
        SELECT
            d.defect_id, d.defect_type, d.severity,
            d.affected_quantity, d.disposition,
            ir.inspection_id, ir.inspected_quantity,
            ir.inspected_at, ir.result,
            po.order_id, po.sku, po.planned_quantity,
            p.name AS product_name,
            ps.step_id, ps.process_name, ps.machine_id,
            ps.temperature, ps.pressure,
            m.machine_name,
            ml.lot_id, ml.material_code,
            ml.received_date, ml.quantity_received,
            s.supplier_id, s.name AS supplier_name,
            s.risk_tier, s.country
        FROM defects d
        JOIN inspection_results ir ON ir.inspection_id = d.inspection_id
        JOIN production_orders po ON po.order_id = d.order_id
        JOIN products p ON p.sku = po.sku
        LEFT JOIN process_steps ps ON ps.step_id = d.step_id
        LEFT JOIN machines m ON m.machine_id = ps.machine_id
        LEFT JOIN material_lots ml ON ml.lot_id = d.lot_id
        LEFT JOIN suppliers s ON s.supplier_id = ml.supplier_id
        WHERE d.defect_id = ?
        """,
        (defect_id,),
    ).fetchone()

    if defect is None:
        db.close()
        raise ValueError(f"Defect not found: {defect_id}")

    capa_rows = db.execute(
        """
        SELECT capa_id, title, root_cause, status,
               opened_date, implemented_date, verified_date, closed_date
        FROM corrective_actions
        WHERE defect_id = ?
        ORDER BY opened_date
        """,
        (defect_id,),
    ).fetchall()

    affected_orders = []
    if defect["lot_id"]:
        affected_orders = db.execute(
            """
            SELECT DISTINCT po.order_id, po.sku, p.name AS product_name,
                   po.planned_quantity, po.status
            FROM material_consumption mc
            JOIN production_orders po ON po.order_id = mc.order_id
            JOIN products p ON p.sku = po.sku
            WHERE mc.lot_id = ?
            ORDER BY po.order_id
            """,
            (defect["lot_id"],),
        ).fetchall()

    db.close()

    return {
        "defect": dict(defect),
        "corrective_actions": [dict(row) for row in capa_rows],
        "affected_orders_from_same_lot": [dict(row) for row in affected_orders],
    }


def trace_order(db_path: str | Path, order_id: str) -> dict:
    """Trace an order to its BOM, consumed lots, suppliers and inspections."""

    db = connect(db_path)

    order = db.execute(
        """
        SELECT po.*, p.name AS product_name, p.category
        FROM production_orders po
        JOIN products p ON p.sku = po.sku
        WHERE po.order_id = ?
        """,
        (order_id,),
    ).fetchone()

    if order is None:
        db.close()
        raise ValueError(f"Production order not found: {order_id}")

    bom = db.execute(
        """
        SELECT material_code, quantity_per_unit, effective_from, effective_to
        FROM bom
        WHERE sku = ?
          AND effective_from <= ?
          AND (effective_to IS NULL OR effective_to >= ?)
        ORDER BY material_code
        """,
        (order["sku"], order["start_date"], order["start_date"]),
    ).fetchall()

    consumption = db.execute(
        """
        SELECT mc.material_code, mc.quantity_used,
               ml.lot_id, ml.received_date,
               s.supplier_id, s.name AS supplier_name, s.risk_tier
        FROM material_consumption mc
        JOIN material_lots ml ON ml.lot_id = mc.lot_id
        JOIN suppliers s ON s.supplier_id = ml.supplier_id
        WHERE mc.order_id = ?
        ORDER BY mc.material_code
        """,
        (order_id,),
    ).fetchall()

    steps = db.execute(
        """
        SELECT ps.*, m.machine_name
        FROM process_steps ps
        JOIN machines m ON m.machine_id = ps.machine_id
        WHERE ps.order_id = ?
        ORDER BY ps.step_number
        """,
        (order_id,),
    ).fetchall()

    inspections = db.execute(
        """
        SELECT ir.*,
               COALESCE(SUM(d.affected_quantity), 0) AS defect_quantity
        FROM inspection_results ir
        LEFT JOIN defects d ON d.inspection_id = ir.inspection_id
        WHERE ir.order_id = ?
        GROUP BY ir.inspection_id
        ORDER BY ir.inspected_at
        """,
        (order_id,),
    ).fetchall()

    defects = db.execute(
        """
        SELECT d.*, ca.capa_id, ca.status AS capa_status,
               ca.root_cause
        FROM defects d
        LEFT JOIN corrective_actions ca ON ca.defect_id = d.defect_id
        WHERE d.order_id = ?
        ORDER BY d.defect_id
        """,
        (order_id,),
    ).fetchall()

    db.close()

    return {
        "order": dict(order),
        "bom": [dict(row) for row in bom],
        "material_consumption": [dict(row) for row in consumption],
        "process_steps": [dict(row) for row in steps],
        "inspections": [dict(row) for row in inspections],
        "defects_and_actions": [dict(row) for row in defects],
    }


def get_dashboard_metrics(db_path: str | Path) -> dict:
    db = connect(db_path)

    metrics = {
        "products": db.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "suppliers": db.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0],
        "production_orders": db.execute(
            "SELECT COUNT(*) FROM production_orders"
        ).fetchone()[0],
        "inspections": db.execute(
            "SELECT COUNT(*) FROM inspection_results"
        ).fetchone()[0],
        "inspected_units": db.execute(
            "SELECT COALESCE(SUM(inspected_quantity), 0) FROM inspection_results"
        ).fetchone()[0],
        "defective_units": db.execute(
            "SELECT COALESCE(SUM(defective_quantity), 0) FROM inspection_results"
        ).fetchone()[0],
        "defect_records": db.execute("SELECT COUNT(*) FROM defects").fetchone()[0],
        "open_capas": db.execute(
            "SELECT COUNT(*) FROM corrective_actions WHERE status != 'CLOSED'"
        ).fetchone()[0],
    }

    metrics["defect_rate_percent"] = round(
        100 * metrics["defective_units"] / metrics["inspected_units"], 2
    ) if metrics["inspected_units"] else 0.0

    db.close()
    return metrics


def supplier_quality_summary(db_path: str | Path) -> list[dict]:
    db = connect(db_path)

    rows = db.execute(
        """
        SELECT s.supplier_id, s.name, s.risk_tier,
               COUNT(DISTINCT ml.lot_id) AS lots_received,
               COUNT(DISTINCT d.defect_id) AS linked_defects,
               COALESCE(SUM(d.affected_quantity), 0) AS affected_units
        FROM suppliers s
        LEFT JOIN material_lots ml ON ml.supplier_id = s.supplier_id
        LEFT JOIN defects d ON d.lot_id = ml.lot_id
        GROUP BY s.supplier_id, s.name, s.risk_tier
        ORDER BY affected_units DESC, linked_defects DESC
        """
    ).fetchall()

    db.close()
    return [dict(row) for row in rows]
