
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    risk_tier TEXT NOT NULL CHECK (risk_tier IN ('LOW','MEDIUM','HIGH')),
    country TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);

CREATE TABLE IF NOT EXISTS products (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (lifecycle_state IN ('ACTIVE','INACTIVE','RETIRED'))
);

CREATE TABLE IF NOT EXISTS bom (
    bom_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL REFERENCES products(sku),
    material_code TEXT NOT NULL,
    quantity_per_unit REAL NOT NULL CHECK (quantity_per_unit > 0),
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    UNIQUE (sku, material_code, effective_from),
    CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE IF NOT EXISTS material_lots (
    lot_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id),
    material_code TEXT NOT NULL,
    received_date TEXT NOT NULL,
    quantity_received INTEGER NOT NULL CHECK (quantity_received > 0),
    quantity_consumed INTEGER NOT NULL DEFAULT 0,
    CHECK (quantity_consumed >= 0 AND quantity_consumed <= quantity_received)
);

CREATE TABLE IF NOT EXISTS machines (
    machine_id TEXT PRIMARY KEY,
    machine_name TEXT NOT NULL,
    process_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','MAINTENANCE','RETIRED'))
);

CREATE TABLE IF NOT EXISTS production_orders (
    order_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL REFERENCES products(sku),
    planned_quantity INTEGER NOT NULL CHECK (planned_quantity > 0),
    start_date TEXT NOT NULL,
    end_date TEXT,
    status TEXT NOT NULL CHECK (status IN ('PLANNED','IN_PROGRESS','COMPLETED','CANCELLED')),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS material_consumption (
    consumption_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES production_orders(order_id),
    lot_id TEXT NOT NULL REFERENCES material_lots(lot_id),
    material_code TEXT NOT NULL,
    quantity_used REAL NOT NULL CHECK (quantity_used > 0)
);

CREATE TABLE IF NOT EXISTS process_steps (
    step_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES production_orders(order_id),
    machine_id TEXT NOT NULL REFERENCES machines(machine_id),
    step_number INTEGER NOT NULL,
    process_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    temperature REAL,
    pressure REAL,
    status TEXT NOT NULL CHECK (status IN ('COMPLETED','FAILED','REWORK')),
    UNIQUE(order_id, step_number),
    CHECK (completed_at >= started_at)
);

CREATE TABLE IF NOT EXISTS inspection_plans (
    plan_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL REFERENCES products(sku),
    inspection_stage TEXT NOT NULL,
    sample_size INTEGER NOT NULL CHECK (sample_size > 0),
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE IF NOT EXISTS inspection_results (
    inspection_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES production_orders(order_id),
    plan_id TEXT NOT NULL REFERENCES inspection_plans(plan_id),
    inspected_at TEXT NOT NULL,
    inspected_quantity INTEGER NOT NULL CHECK (inspected_quantity > 0),
    defective_quantity INTEGER NOT NULL DEFAULT 0,
    result TEXT NOT NULL CHECK (result IN ('PASS','FAIL')),
    CHECK (defective_quantity >= 0 AND defective_quantity <= inspected_quantity),
    CHECK (
        (defective_quantity = 0 AND result = 'PASS') OR
        (defective_quantity > 0 AND result = 'FAIL')
    )
);

CREATE TABLE IF NOT EXISTS defects (
    defect_id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL REFERENCES inspection_results(inspection_id),
    order_id TEXT NOT NULL REFERENCES production_orders(order_id),
    step_id TEXT REFERENCES process_steps(step_id),
    lot_id TEXT REFERENCES material_lots(lot_id),
    defect_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    affected_quantity INTEGER NOT NULL CHECK (affected_quantity > 0),
    disposition TEXT NOT NULL CHECK (disposition IN ('REWORK','SCRAP','USE_AS_IS','PENDING'))
);

CREATE TABLE IF NOT EXISTS corrective_actions (
    capa_id TEXT PRIMARY KEY,
    defect_id TEXT NOT NULL REFERENCES defects(defect_id),
    title TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('OPEN','CONTAINMENT','INVESTIGATING','IMPLEMENTED','VERIFIED','CLOSED')
    ),
    opened_date TEXT NOT NULL,
    implemented_date TEXT,
    verified_date TEXT,
    closed_date TEXT,
    CHECK (implemented_date IS NULL OR implemented_date >= opened_date),
    CHECK (verified_date IS NULL OR (implemented_date IS NOT NULL AND verified_date >= implemented_date)),
    CHECK (closed_date IS NULL OR (verified_date IS NOT NULL AND closed_date >= verified_date)),
    CHECK (status != 'CLOSED' OR (verified_date IS NOT NULL AND closed_date IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS lifecycle_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT NOT NULL,
    event_date TEXT NOT NULL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_lots_supplier ON material_lots(supplier_id);
CREATE INDEX IF NOT EXISTS idx_consumption_order ON material_consumption(order_id);
CREATE INDEX IF NOT EXISTS idx_consumption_lot ON material_consumption(lot_id);
CREATE INDEX IF NOT EXISTS idx_steps_order ON process_steps(order_id);
CREATE INDEX IF NOT EXISTS idx_inspections_order ON inspection_results(order_id);
CREATE INDEX IF NOT EXISTS idx_defects_order ON defects(order_id);
CREATE INDEX IF NOT EXISTS idx_defects_lot ON defects(lot_id);
CREATE INDEX IF NOT EXISTS idx_capa_status ON corrective_actions(status);
