
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from traceforge.generator import generate

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", choices=["starter", "full"], default="starter")
    parser.add_argument("--seed", type=int, default=20261022)
    args = parser.parse_args()

    result = generate(scale=args.scale, seed=args.seed)
    print("\nTraceForge data generation completed!")
    print(f"Scale: {result['scale']}")
    print(f"Seed: {result['seed']}")
    print("Records:", result["record_counts"])
