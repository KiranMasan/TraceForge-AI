
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from traceforge.validation import validate_database

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", choices=["starter", "full"], default="starter")
    args = parser.parse_args()

    db_path = PROJECT_ROOT / "data" / "generated" / args.scale / "traceforge.db"
    report = validate_database(db_path)

    report_path = db_path.parent / "validation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"\nValidation report saved to: {report_path}")

    if not report["valid"]:
        raise SystemExit(1)
