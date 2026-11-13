
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from traceforge.anomaly_detector import run_detection


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", choices=["starter", "full"], default="starter")
    args = parser.parse_args()

    output_dir = PROJECT_ROOT / "data" / "generated" / args.scale
    db_path = output_dir / "traceforge.db"
    anomaly_path = output_dir / "anomaly_cases.json"
    truth_path = (
        PROJECT_ROOT / "data" / "ground_truth" /
        f"{args.scale}_ground_truth.json"
    )

    report = run_detection(db_path, anomaly_path, truth_path)

    report_path = output_dir / "anomaly_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"\nAnomaly report saved to: {report_path}")

    if report["metrics"]["recall"] < 1.0:
        raise SystemExit("Not all labelled anomalies were detected.")
