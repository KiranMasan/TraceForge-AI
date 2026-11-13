
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from traceforge.services import (
    get_dashboard_metrics,
    supplier_quality_summary,
    trace_defect,
    trace_order,
)

DB = PROJECT_ROOT / "data" / "generated" / "starter" / "traceforge.db"

if __name__ == "__main__":
    metrics = get_dashboard_metrics(DB)
    print("\n=== TRACEFORGE MANUFACTURING OVERVIEW ===")
    print(json.dumps(metrics, indent=2))

    import sqlite3

    connection = sqlite3.connect(DB)
    defect = connection.execute(
        "SELECT defect_id FROM defects ORDER BY defect_id LIMIT 1"
    ).fetchone()
    order = connection.execute(
        "SELECT order_id FROM production_orders ORDER BY order_id LIMIT 1"
    ).fetchone()
    connection.close()

    if defect:
        print("\n=== DEFECT TRACE ===")
        print(json.dumps(trace_defect(DB, defect[0]), indent=2))

    if order:
        print("\n=== PRODUCTION ORDER TRACE ===")
        print(json.dumps(trace_order(DB, order[0]), indent=2))

    print("\n=== SUPPLIER QUALITY ===")
    print(json.dumps(supplier_quality_summary(DB), indent=2))
