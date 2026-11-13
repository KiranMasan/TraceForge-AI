from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from .services import (
    get_dashboard_metrics,
    supplier_quality_summary,
    trace_defect,
    trace_order,
)


ID_PATTERNS = {
    "defect": r"\bDEF-\d{4}-\d{6}\b",
    "order": r"\bWO-\d{4}-\d{6}\b",
    "product": r"\bSKU-\d{6}\b",
    "supplier": r"\bSUP-\d{6}\b",
    "lot": r"\bLOT-SUP-\d{6}-\d{4}-\d{6}\b",
}


def _connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _find_ids(question: str) -> dict:
    found = {}

    for entity, pattern in ID_PATTERNS.items():
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            found[entity] = match.group(0).upper()

    return found


def _defect_type_summary(db_path: str | Path) -> list[dict]:
    with _connect(db_path) as db:
        rows = db.execute("""
            SELECT
                defect_type,
                COUNT(*) AS defect_records,
                SUM(affected_quantity) AS affected_units
            FROM defects
            GROUP BY defect_type
            ORDER BY defect_records DESC
        """).fetchall()

    return [dict(row) for row in rows]


def _product_investigation(
    db_path: str | Path, sku: str
) -> dict:
    with _connect(db_path) as db:
        product = db.execute("""
            SELECT sku, name, category, lifecycle_state
            FROM products
            WHERE sku = ?
        """, (sku,)).fetchone()

        if product is None:
            raise ValueError(f"Product not found: {sku}")

        orders = db.execute("""
            SELECT
                po.order_id,
                po.status,
                po.planned_quantity,
                COUNT(DISTINCT d.defect_id) AS defect_records,
                COALESCE(SUM(d.affected_quantity), 0) AS affected_units
            FROM production_orders po
            LEFT JOIN defects d ON d.order_id = po.order_id
            WHERE po.sku = ?
            GROUP BY po.order_id
            ORDER BY defect_records DESC, po.order_id
            LIMIT 20
        """, (sku,)).fetchall()

        defects = db.execute("""
            SELECT
                d.defect_id,
                d.defect_type,
                d.severity,
                d.affected_quantity,
                d.order_id,
                d.lot_id,
                ca.capa_id,
                ca.status AS capa_status
            FROM defects d
            JOIN production_orders po ON po.order_id = d.order_id
            LEFT JOIN corrective_actions ca ON ca.defect_id = d.defect_id
            WHERE po.sku = ?
            ORDER BY d.affected_quantity DESC
            LIMIT 30
        """, (sku,)).fetchall()

    return {
        "product": dict(product),
        "production_orders": [dict(row) for row in orders],
        "defects": [dict(row) for row in defects],
    }


def _supplier_investigation(
    db_path: str | Path, supplier_id: str
) -> dict:
    with _connect(db_path) as db:
        supplier = db.execute("""
            SELECT supplier_id, name, risk_tier, country, active
            FROM suppliers
            WHERE supplier_id = ?
        """, (supplier_id,)).fetchone()

        if supplier is None:
            raise ValueError(f"Supplier not found: {supplier_id}")

        lots = db.execute("""
            SELECT
                ml.lot_id,
                ml.material_code,
                ml.received_date,
                ml.quantity_received,
                COUNT(DISTINCT d.defect_id) AS linked_defects,
                COALESCE(SUM(d.affected_quantity), 0) AS affected_units
            FROM material_lots ml
            LEFT JOIN defects d ON d.lot_id = ml.lot_id
            WHERE ml.supplier_id = ?
            GROUP BY ml.lot_id
            ORDER BY linked_defects DESC, ml.lot_id
            LIMIT 30
        """, (supplier_id,)).fetchall()

        defects = db.execute("""
            SELECT
                d.defect_id,
                d.defect_type,
                d.severity,
                d.affected_quantity,
                d.order_id,
                d.lot_id,
                ca.capa_id,
                ca.status AS capa_status
            FROM defects d
            JOIN material_lots ml ON ml.lot_id = d.lot_id
            LEFT JOIN corrective_actions ca ON ca.defect_id = d.defect_id
            WHERE ml.supplier_id = ?
            ORDER BY d.affected_quantity DESC
            LIMIT 30
        """, (supplier_id,)).fetchall()

    return {
        "supplier": dict(supplier),
        "material_lots": [dict(row) for row in lots],
        "linked_defects": [dict(row) for row in defects],
    }


def _lot_investigation(db_path: str | Path, lot_id: str) -> dict:
    with _connect(db_path) as db:
        lot = db.execute("""
            SELECT
                ml.lot_id,
                ml.material_code,
                ml.received_date,
                ml.quantity_received,
                ml.quantity_consumed,
                s.supplier_id,
                s.name AS supplier_name,
                s.risk_tier
            FROM material_lots ml
            JOIN suppliers s ON s.supplier_id = ml.supplier_id
            WHERE ml.lot_id = ?
        """, (lot_id,)).fetchone()

        if lot is None:
            raise ValueError(f"Material lot not found: {lot_id}")

        orders = db.execute("""
            SELECT DISTINCT
                po.order_id,
                po.sku,
                po.status,
                mc.quantity_used
            FROM material_consumption mc
            JOIN production_orders po ON po.order_id = mc.order_id
            WHERE mc.lot_id = ?
            ORDER BY po.order_id
        """, (lot_id,)).fetchall()

        defects = db.execute("""
            SELECT
                defect_id, defect_type, severity,
                affected_quantity, order_id
            FROM defects
            WHERE lot_id = ?
            ORDER BY defect_id
        """, (lot_id,)).fetchall()

    return {
        "material_lot": dict(lot),
        "production_orders": [dict(row) for row in orders],
        "defects": [dict(row) for row in defects],
    }


def _source_references(evidence: dict) -> list[str]:
    references = set()

    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {
                    "defect_id", "order_id", "sku",
                    "supplier_id", "lot_id", "capa_id",
                    "inspection_id", "step_id",
                } and isinstance(item, str):
                    references.add(item)

                visit(item)

        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(evidence)
    return sorted(references)


def retrieve_evidence(
    db_path: str | Path,
    question: str,
) -> dict:
    """Retrieve manufacturing evidence for a Copilot investigation."""

    if not question or not question.strip():
        raise ValueError("Please enter an investigation question.")

    database = Path(db_path)

    if not database.is_file():
        raise FileNotFoundError(f"Database not found: {database}")

    ids = _find_ids(question)
    evidence = {}
    investigation_type = "general"

    if "defect" in ids:
        investigation_type = "defect"
        evidence = trace_defect(database, ids["defect"])

    elif "order" in ids:
        investigation_type = "order"
        evidence = trace_order(database, ids["order"])

    elif "product" in ids:
        investigation_type = "product"
        evidence = _product_investigation(database, ids["product"])

    elif "supplier" in ids:
        investigation_type = "supplier"
        evidence = _supplier_investigation(
            database, ids["supplier"]
        )

    elif "lot" in ids:
        investigation_type = "material_lot"
        evidence = _lot_investigation(database, ids["lot"])

    elif any(word in question.lower() for word in (
        "supplier", "vendor"
    )):
        investigation_type = "supplier_quality"
        evidence = {
            "supplier_quality": supplier_quality_summary(database)
        }

    elif any(word in question.lower() for word in (
        "defect", "failure", "quality", "trend"
    )):
        investigation_type = "defect_analysis"
        evidence = {
            "defect_type_summary": _defect_type_summary(database)
        }

    else:
        evidence = {
            "dashboard_metrics": get_dashboard_metrics(database),
            "defect_type_summary": _defect_type_summary(database),
            "supplier_quality": supplier_quality_summary(database),
        }

    return {
        "question": question.strip(),
        "investigation_type": investigation_type,
        "matched_ids": ids,
        "evidence": evidence,
        "source_references": _source_references(evidence),
    }


def answer_with_ollama(
    investigation: dict,
    model: str = "llama3.2:3b",
    timeout: int = 90,
) -> str:
    """Generate an evidence-grounded explanation using local Ollama."""

    from urllib.error import URLError
    from urllib.request import Request, urlopen

    prompt = f"""
You are TraceForge Copilot, a manufacturing quality investigation assistant.

Answer the user's question using ONLY the supplied database evidence.

Rules:
- Never invent production records, measurements, causes, or statistics.
- Separate verified facts from possible explanations.
- If evidence is insufficient, say so explicitly.
- Cite relevant source record IDs in your answer.
- Do not claim correlation proves causation.
- Suggest practical next investigation steps.

User question:
{investigation["question"]}

Investigation type:
{investigation["investigation_type"]}

Matched identifiers:
{json.dumps(investigation["matched_ids"], ensure_ascii=False)}

Database evidence:
{json.dumps(investigation["evidence"], ensure_ascii=False, default=str)}

Write a concise investigation report with:
1. Findings
2. Supporting evidence and record IDs
3. Possible explanations (clearly marked as hypotheses)
4. Recommended next steps
"""

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }).encode("utf-8")

    request = Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

        answer = result.get("response", "").strip()

        if not answer:
            raise RuntimeError("Ollama returned an empty response.")

        return answer

    except (URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"Could not reach Ollama. Check that it is running: {exc}"
        ) from exc


def investigate(
    db_path: str | Path,
    question: str,
    use_llm: bool = True,
    model: str = "llama3.2:3b",
) -> dict:
    """Retrieve evidence and optionally generate an Ollama explanation."""

    result = retrieve_evidence(db_path, question)

    if use_llm:
        result["answer"] = answer_with_ollama(result, model=model)
    else:
        result["answer"] = None

    return result
