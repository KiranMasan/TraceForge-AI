
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED = 20261022

SCALES = {
    "starter": {"products": 20, "suppliers": 10, "lots": 100, "orders": 100, "inspections": 400},
    "full": {"products": 200, "suppliers": 50, "lots": 2000, "orders": 5000, "inspections": 20000},
}

START_DATE = date(2026, 1, 1)


def iso_day(rng: random.Random, start=START_DATE, days=300) -> str:
    return (start + timedelta(days=rng.randint(0, days))).isoformat()


def write_csvs(connection: sqlite3.Connection, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = []

    tables = [
        "suppliers", "products", "bom", "material_lots", "machines",
        "production_orders", "material_consumption", "process_steps",
        "inspection_plans", "inspection_results", "defects",
        "corrective_actions", "lifecycle_events",
    ]

    for table in tables:
        path = output_dir / f"{table}.csv"
        cursor = connection.execute(f"SELECT * FROM {table}")
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([column[0] for column in cursor.description])
            writer.writerows(cursor.fetchall())
        files.append(path)

    return files


def generate(scale: str = "starter", seed: int = DEFAULT_SEED) -> dict:
    if scale not in SCALES:
        raise ValueError(f"Unknown scale: {scale}. Choose starter or full.")

    rng = random.Random(seed)
    counts = SCALES[scale]

    output_dir = ROOT / "data" / "generated" / scale
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "traceforge.db"

    if db_path.exists():
        db_path.unlink()

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    schema_path = ROOT / "src" / "traceforge" / "schema.sql"
    connection.executescript(schema_path.read_text(encoding="utf-8"))

    suppliers = []
    for i in range(1, counts["suppliers"] + 1):
        supplier_id = f"SUP-{i:06d}"
        tier = rng.choices(["LOW", "MEDIUM", "HIGH"], weights=[55, 30, 15])[0]
        suppliers.append((supplier_id, f"Supplier {i:03d}", tier,
                          rng.choice(["India", "Germany", "Japan", "USA"]), 1))

    connection.executemany(
        "INSERT INTO suppliers VALUES (?, ?, ?, ?, ?)", suppliers
    )

    products = []
    bom_rows = []
    product_materials = {}

    material_count = counts["products"] * 2
    for i in range(1, counts["products"] + 1):
        sku = f"SKU-{i:06d}"
        products.append((sku, f"Manufactured Product {i:03d}",
                         rng.choice(["Electronics", "Automotive", "Industrial"]),
                         "ACTIVE"))
        materials = [f"MAT-{(i - 1) * 2 + 1:06d}",
                     f"MAT-{(i - 1) * 2 + 2:06d}"]
        product_materials[sku] = materials
        for material in materials:
            bom_rows.append((sku, material, rng.choice([1.0, 1.0, 1.5, 2.0]),
                             "2026-01-01", None))

    connection.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products)
    connection.executemany(
        """INSERT INTO bom
           (sku, material_code, quantity_per_unit, effective_from, effective_to)
           VALUES (?, ?, ?, ?, ?)""",
        bom_rows,
    )

    machines = []
    for i in range(1, 21):
        machines.append((f"MCH-{i:04d}", f"Production Machine {i:02d}",
                         rng.choice(["ASSEMBLY", "WELDING", "PAINTING", "PACKAGING"]),
                         "ACTIVE"))
    connection.executemany("INSERT INTO machines VALUES (?, ?, ?, ?)", machines)

    # Each material receives five or more available lots across its suppliers.
    lot_pools: dict[str, list[dict]] = {f"MAT-{i:06d}": [] for i in range(1, material_count + 1)}
    lot_rows = []
    supplier_lot_sequence = 0

    for lot_number in range(1, counts["lots"] + 1):
        supplier = suppliers[(lot_number - 1) % len(suppliers)]
        material = f"MAT-{((lot_number - 1) % material_count) + 1:06d}"
        lot_id = f"LOT-{supplier[0]}-2026-{lot_number:06d}"
        received = 100000
        lot = {
            "lot_id": lot_id,
            "supplier_id": supplier[0],
            "material_code": material,
            "received_date": (
                date(2025, 12, 1) + timedelta(days=rng.randint(0, 25))
            ).isoformat(),
            "quantity_received": received,
            "quantity_consumed": 0,
        }
        lot_pools[material].append(lot)
        lot_rows.append((lot_id, supplier[0], material, lot["received_date"], received, 0))

    connection.executemany(
        "INSERT INTO material_lots VALUES (?, ?, ?, ?, ?, ?)", lot_rows
    )

    # One effective inspection plan per product.
    plan_rows = []
    for i in range(1, counts["products"] + 1):
        plan_rows.append((f"PLAN-{i:06d}", f"SKU-{i:06d}",
                          "FINAL", 50, "2026-01-01", None))
    connection.executemany(
        """INSERT INTO inspection_plans
           (plan_id, sku, inspection_stage, sample_size, effective_from, effective_to)
           VALUES (?, ?, ?, ?, ?, ?)""",
        plan_rows,
    )

    # Generate orders and their valid material consumption/process history.
    order_rows = []
    consumption_rows = []
    step_rows = []
    order_lots = {}
    order_steps = {}

    for i in range(1, counts["orders"] + 1):
        order_id = f"WO-2026-{i:06d}"
        sku = f"SKU-{rng.randint(1, counts['products']):06d}"
        quantity = rng.randint(50, 300)
        start = iso_day(rng)
        end = (date.fromisoformat(start) + timedelta(days=rng.randint(0, 4))).isoformat()
        order_rows.append((order_id, sku, quantity, start, end, "COMPLETED"))

        consumed_lots = []
        for material in product_materials[sku]:
            bom_item = next(row for row in bom_rows if row[0] == sku and row[1] == material)
            required = quantity * bom_item[2]
            candidates = lot_pools[material]
            if not candidates:
                raise RuntimeError(f"No material lots available for {material}")
            lot = candidates[(i - 1) % len(candidates)]
            lot["quantity_consumed"] += int(required)
            consumption_rows.append((order_id, lot["lot_id"], material, required))
            consumed_lots.append(lot["lot_id"])

        order_lots[order_id] = consumed_lots

        step_ids = []
        for step_no in (1, 2):
            step_id = f"STEP-{order_id}-{step_no:03d}"
            machine_id = f"MCH-{rng.randint(1, 20):04d}"
            started = f"{start}T{8 + step_no:02d}:00:00"
            completed = f"{start}T{9 + step_no:02d}:00:00"
            process = "ASSEMBLY" if step_no == 1 else "FINISHING"
            drift = rng.random() < 0.10
            temperature = round(rng.uniform(180, 220) + (18 if drift else 0), 2)
            pressure = round(rng.uniform(30, 45) + (8 if drift else 0), 2)
            step_rows.append((step_id, order_id, machine_id, step_no, process,
                              started, completed, temperature, pressure, "COMPLETED"))
            step_ids.append(step_id)
        order_steps[order_id] = step_ids

    connection.executemany(
        "INSERT INTO production_orders VALUES (?, ?, ?, ?, ?, ?)", order_rows
    )
    connection.executemany(
        """INSERT INTO material_consumption
           (order_id, lot_id, material_code, quantity_used)
           VALUES (?, ?, ?, ?)""",
        consumption_rows,
    )
    connection.executemany(
        "INSERT INTO process_steps VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        step_rows,
    )

    # Update lot balances from the consumption bridge.
    for lot in lot_rows:
        lot_id = lot[0]
        consumed = sum(
            row[3] for row in consumption_rows if row[1] == lot_id
        )
        connection.execute(
            "UPDATE material_lots SET quantity_consumed = ? WHERE lot_id = ?",
            (int(consumed), lot_id),
        )

    # Inspection results: four inspections per order in the full dataset.
    inspection_rows = []
    defect_rows = []
    capa_rows = []
    event_rows = []
    defect_sequence = 0

    for i in range(1, counts["inspections"] + 1):
        order_index = ((i - 1) % counts["orders"]) + 1
        order_id = f"WO-2026-{order_index:06d}"
        sku = order_rows[order_index - 1][1]
        plan_id = f"PLAN-{int(sku.split('-')[1]):06d}"
        inspection_slot = (i - 1) // counts["orders"]

        planned_quantity = order_rows[order_index - 1][2]

        base_quantity = planned_quantity // 4
        remainder = planned_quantity % 4

        inspected = base_quantity + (
            1 if inspection_slot < remainder else 0
        )

        # Supplier risk and occasional process drift influence defect probability.
        lot_id = order_lots[order_id][0]
        supplier_id = next(lot[1] for lot in lot_rows if lot[0] == lot_id)
        risk = next(s[2] for s in suppliers if s[0] == supplier_id)
        probability = {"LOW": 0.035, "MEDIUM": 0.065, "HIGH": 0.11}[risk]
        if rng.random() < 0.10:
            probability += 0.10

        if rng.random() < probability:
             defective = rng.randint(1, max(1, min(5, inspected // 10)))
        else:
            defective = 0
        inspected_at = order_rows[order_index - 1][4] + "T16:00:00"
        inspection_id = f"INSP-{order_id}-{((i - 1) // counts['orders']) + 1:03d}"
        result = "FAIL" if defective else "PASS"

        inspection_rows.append((inspection_id, order_id, plan_id, inspected_at,
                                inspected, defective, result))

        if defective:
            defect_sequence += 1
            defect_id = f"DEF-2026-{defect_sequence:06d}"
            step_id = rng.choice(order_steps[order_id])
            disposition = rng.choices(
                ["REWORK", "SCRAP", "USE_AS_IS", "PENDING"],
                weights=[45, 20, 10, 25],
            )[0]
            severity = rng.choices(
                ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                weights=[35, 35, 22, 8],
            )[0]
            defect_rows.append((defect_id, inspection_id, order_id, step_id,
                                lot_id, rng.choice(["DIMENSIONAL", "SURFACE",
                                                   "ASSEMBLY", "ELECTRICAL"]),
                                severity, defective, disposition))

            capa_id = f"CAPA-2026-{defect_sequence:06d}"
            opened = inspected_at[:10]
            lifecycle = rng.choice(["OPEN", "INVESTIGATING", "IMPLEMENTED", "CLOSED"])
            implemented = None
            verified = None
            closed = None

            if lifecycle in ("IMPLEMENTED", "CLOSED"):
                implemented = (date.fromisoformat(opened) + timedelta(days=2)).isoformat()
            if lifecycle == "CLOSED":
                verified = (date.fromisoformat(implemented) + timedelta(days=2)).isoformat()
                closed = (date.fromisoformat(verified) + timedelta(days=1)).isoformat()

            capa_rows.append((capa_id, defect_id, "Investigate manufacturing defect",
                              rng.choice(["Supplier material variation",
                                          "Process parameter drift",
                                          "Machine calibration issue"]),
                              lifecycle, opened, implemented, verified, closed))
            event_rows.append(("CAPA", capa_id, None, lifecycle, opened,
                               "Initial corrective-action state"))

    connection.executemany(
        "INSERT INTO inspection_results VALUES (?, ?, ?, ?, ?, ?, ?)",
        inspection_rows,
    )
    connection.executemany(
        "INSERT INTO defects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        defect_rows,
    )
    connection.executemany(
        """INSERT INTO corrective_actions
           (capa_id, defect_id, title, root_cause, status, opened_date,
            implemented_date, verified_date, closed_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        capa_rows,
    )
    connection.executemany(
        """INSERT INTO lifecycle_events
           (entity_type, entity_id, from_state, to_state, event_date, notes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        event_rows,
    )

    connection.commit()

    # Deliberately invalid examples are stored outside the valid operational DB.
    anomaly_cases = [
        {"case_id": "EDGE-001", "type": "NONEXISTENT_LOT_REFERENCE",
         "record": {"order_id": "WO-2026-000001", "lot_id": "LOT-DOES-NOT-EXIST"}},
       {
            "case_id": "EDGE-002",
            "type": "BOM_MATERIAL_NOT_CONSUMED",
            "record": {
                "order_id": "WO-2026-000002",
                "bom_material": product_materials[order_rows[1][1]][0],
                "required_materials": product_materials[order_rows[1][1]],
                "consumed_materials": [product_materials[order_rows[1][1]][1]]
            }
        },
        {"case_id": "EDGE-003", "type": "CAPA_CLOSED_BEFORE_VERIFICATION",
         "record": {"capa_id": "CAPA-EDGE-003", "status": "CLOSED",
                    "verified_date": None, "closed_date": "2026-10-20"}},
        {"case_id": "EDGE-004", "type": "DEFECTS_EXCEED_INSPECTED_QUANTITY",
         "record": {"inspection_id": "INSP-EDGE-004",
                    "inspected_quantity": 20, "defective_quantity": 25}},
        {"case_id": "EDGE-005", "type": "BROKEN_TRACEABILITY",
         "record": {"defect_id": "DEF-EDGE-005", "order_id": None,
                    "lot_id": None, "step_id": None}},
    ]
    truth = {case["case_id"]: {"is_anomaly": True, "expected_type": case["type"]}
             for case in anomaly_cases}

    anomaly_path = output_dir / "anomaly_cases.json"
    truth_path = ROOT / "data" / "ground_truth" / f"{scale}_ground_truth.json"
    truth_path.parent.mkdir(parents=True, exist_ok=True)
    anomaly_path.write_text(json.dumps(anomaly_cases, indent=2), encoding="utf-8")
    truth_path.write_text(json.dumps(truth, indent=2), encoding="utf-8")

    csv_files = write_csvs(connection, output_dir)
    connection.close()

    # Hash deterministic exports and anomaly fixtures, not the SQLite binary.
    manifest_files = csv_files + [anomaly_path]
    manifest = {
        "project": "TraceForge AI",
        "scale": scale,
        "seed": seed,
        "generated_on": "2026-11-13",
        "record_counts": {
            "products": counts["products"],
            "suppliers": counts["suppliers"],
            "material_lots": counts["lots"],
            "production_orders": counts["orders"],
            "inspection_results": counts["inspections"],
            "defects": len(defect_rows),
            "corrective_actions": len(capa_rows),
        },
        "sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in manifest_files
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate TraceForge manufacturing data")
    parser.add_argument("--scale", choices=["starter", "full"], default="starter")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    result = generate(args.scale, args.seed)
    print(json.dumps(result, indent=2))
