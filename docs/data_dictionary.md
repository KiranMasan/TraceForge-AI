# TraceForge AI - Data Dictionary

Generated directly from `src/traceforge/schema.sql`.

## 1. Database overview

The database contains 13 relational tables for manufacturing traceability,
quality inspection, defect investigation, and corrective action management.

## 2. Column definitions

SQLite type, nullability, primary key, default, and foreign-key details
below reflect the schema. Business units are not specified unless documented
elsewhere in the project.

## bom

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `bom_id` | INTEGER | No | Yes | `-` |
| `sku` | TEXT | Yes | No | `-` |
| `material_code` | TEXT | Yes | No | `-` |
| `quantity_per_unit` | REAL | Yes | No | `-` |
| `effective_from` | TEXT | Yes | No | `-` |
| `effective_to` | TEXT | No | No | `-` |

**Foreign keys**

- `sku` references `products.sku`.

**Declared table constraints**

```sql
CREATE TABLE bom (
    bom_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL REFERENCES products(sku),
    material_code TEXT NOT NULL,
    quantity_per_unit REAL NOT NULL CHECK (quantity_per_unit > 0),
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    UNIQUE (sku, material_code, effective_from),
    CHECK (effective_to IS NULL OR effective_to >= effective_from)
)
```

## corrective_actions

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `capa_id` | TEXT | No | Yes | `-` |
| `defect_id` | TEXT | Yes | No | `-` |
| `title` | TEXT | Yes | No | `-` |
| `root_cause` | TEXT | Yes | No | `-` |
| `status` | TEXT | Yes | No | `-` |
| `opened_date` | TEXT | Yes | No | `-` |
| `implemented_date` | TEXT | No | No | `-` |
| `verified_date` | TEXT | No | No | `-` |
| `closed_date` | TEXT | No | No | `-` |

**Foreign keys**

- `defect_id` references `defects.defect_id`.

**Declared table constraints**

```sql
CREATE TABLE corrective_actions (
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
)
```

## defects

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `defect_id` | TEXT | No | Yes | `-` |
| `inspection_id` | TEXT | Yes | No | `-` |
| `order_id` | TEXT | Yes | No | `-` |
| `step_id` | TEXT | No | No | `-` |
| `lot_id` | TEXT | No | No | `-` |
| `defect_type` | TEXT | Yes | No | `-` |
| `severity` | TEXT | Yes | No | `-` |
| `affected_quantity` | INTEGER | Yes | No | `-` |
| `disposition` | TEXT | Yes | No | `-` |

**Foreign keys**

- `lot_id` references `material_lots.lot_id`.
- `step_id` references `process_steps.step_id`.
- `order_id` references `production_orders.order_id`.
- `inspection_id` references `inspection_results.inspection_id`.

**Declared table constraints**

```sql
CREATE TABLE defects (
    defect_id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL REFERENCES inspection_results(inspection_id),
    order_id TEXT NOT NULL REFERENCES production_orders(order_id),
    step_id TEXT REFERENCES process_steps(step_id),
    lot_id TEXT REFERENCES material_lots(lot_id),
    defect_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    affected_quantity INTEGER NOT NULL CHECK (affected_quantity > 0),
    disposition TEXT NOT NULL CHECK (disposition IN ('REWORK','SCRAP','USE_AS_IS','PENDING'))
)
```

## inspection_plans

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `plan_id` | TEXT | No | Yes | `-` |
| `sku` | TEXT | Yes | No | `-` |
| `inspection_stage` | TEXT | Yes | No | `-` |
| `sample_size` | INTEGER | Yes | No | `-` |
| `effective_from` | TEXT | Yes | No | `-` |
| `effective_to` | TEXT | No | No | `-` |

**Foreign keys**

- `sku` references `products.sku`.

**Declared table constraints**

```sql
CREATE TABLE inspection_plans (
    plan_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL REFERENCES products(sku),
    inspection_stage TEXT NOT NULL,
    sample_size INTEGER NOT NULL CHECK (sample_size > 0),
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    CHECK (effective_to IS NULL OR effective_to >= effective_from)
)
```

## inspection_results

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `inspection_id` | TEXT | No | Yes | `-` |
| `order_id` | TEXT | Yes | No | `-` |
| `plan_id` | TEXT | Yes | No | `-` |
| `inspected_at` | TEXT | Yes | No | `-` |
| `inspected_quantity` | INTEGER | Yes | No | `-` |
| `defective_quantity` | INTEGER | Yes | No | `0` |
| `result` | TEXT | Yes | No | `-` |

**Foreign keys**

- `plan_id` references `inspection_plans.plan_id`.
- `order_id` references `production_orders.order_id`.

**Declared table constraints**

```sql
CREATE TABLE inspection_results (
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
)
```

## lifecycle_events

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `event_id` | INTEGER | No | Yes | `-` |
| `entity_type` | TEXT | Yes | No | `-` |
| `entity_id` | TEXT | Yes | No | `-` |
| `from_state` | TEXT | No | No | `-` |
| `to_state` | TEXT | Yes | No | `-` |
| `event_date` | TEXT | Yes | No | `-` |
| `notes` | TEXT | No | No | `-` |

**Foreign keys**

- No declared foreign keys.

**Declared table constraints**

```sql
CREATE TABLE lifecycle_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT NOT NULL,
    event_date TEXT NOT NULL,
    notes TEXT
)
```

## machines

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `machine_id` | TEXT | No | Yes | `-` |
| `machine_name` | TEXT | Yes | No | `-` |
| `process_type` | TEXT | Yes | No | `-` |
| `status` | TEXT | Yes | No | `-` |

**Foreign keys**

- No declared foreign keys.

**Declared table constraints**

```sql
CREATE TABLE machines (
    machine_id TEXT PRIMARY KEY,
    machine_name TEXT NOT NULL,
    process_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','MAINTENANCE','RETIRED'))
)
```

## material_consumption

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `consumption_id` | INTEGER | No | Yes | `-` |
| `order_id` | TEXT | Yes | No | `-` |
| `lot_id` | TEXT | Yes | No | `-` |
| `material_code` | TEXT | Yes | No | `-` |
| `quantity_used` | REAL | Yes | No | `-` |

**Foreign keys**

- `lot_id` references `material_lots.lot_id`.
- `order_id` references `production_orders.order_id`.

**Declared table constraints**

```sql
CREATE TABLE material_consumption (
    consumption_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES production_orders(order_id),
    lot_id TEXT NOT NULL REFERENCES material_lots(lot_id),
    material_code TEXT NOT NULL,
    quantity_used REAL NOT NULL CHECK (quantity_used > 0)
)
```

## material_lots

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `lot_id` | TEXT | No | Yes | `-` |
| `supplier_id` | TEXT | Yes | No | `-` |
| `material_code` | TEXT | Yes | No | `-` |
| `received_date` | TEXT | Yes | No | `-` |
| `quantity_received` | INTEGER | Yes | No | `-` |
| `quantity_consumed` | INTEGER | Yes | No | `0` |

**Foreign keys**

- `supplier_id` references `suppliers.supplier_id`.

**Declared table constraints**

```sql
CREATE TABLE material_lots (
    lot_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id),
    material_code TEXT NOT NULL,
    received_date TEXT NOT NULL,
    quantity_received INTEGER NOT NULL CHECK (quantity_received > 0),
    quantity_consumed INTEGER NOT NULL DEFAULT 0,
    CHECK (quantity_consumed >= 0 AND quantity_consumed <= quantity_received)
)
```

## process_steps

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `step_id` | TEXT | No | Yes | `-` |
| `order_id` | TEXT | Yes | No | `-` |
| `machine_id` | TEXT | Yes | No | `-` |
| `step_number` | INTEGER | Yes | No | `-` |
| `process_name` | TEXT | Yes | No | `-` |
| `started_at` | TEXT | Yes | No | `-` |
| `completed_at` | TEXT | Yes | No | `-` |
| `temperature` | REAL | No | No | `-` |
| `pressure` | REAL | No | No | `-` |
| `status` | TEXT | Yes | No | `-` |

**Foreign keys**

- `machine_id` references `machines.machine_id`.
- `order_id` references `production_orders.order_id`.

**Declared table constraints**

```sql
CREATE TABLE process_steps (
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
)
```

## production_orders

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `order_id` | TEXT | No | Yes | `-` |
| `sku` | TEXT | Yes | No | `-` |
| `planned_quantity` | INTEGER | Yes | No | `-` |
| `start_date` | TEXT | Yes | No | `-` |
| `end_date` | TEXT | No | No | `-` |
| `status` | TEXT | Yes | No | `-` |

**Foreign keys**

- `sku` references `products.sku`.

**Declared table constraints**

```sql
CREATE TABLE production_orders (
    order_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL REFERENCES products(sku),
    planned_quantity INTEGER NOT NULL CHECK (planned_quantity > 0),
    start_date TEXT NOT NULL,
    end_date TEXT,
    status TEXT NOT NULL CHECK (status IN ('PLANNED','IN_PROGRESS','COMPLETED','CANCELLED')),
    CHECK (end_date IS NULL OR end_date >= start_date)
)
```

## products

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `sku` | TEXT | No | Yes | `-` |
| `name` | TEXT | Yes | No | `-` |
| `category` | TEXT | Yes | No | `-` |
| `lifecycle_state` | TEXT | Yes | No | `'ACTIVE'` |

**Foreign keys**

- No declared foreign keys.

**Declared table constraints**

```sql
CREATE TABLE products (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (lifecycle_state IN ('ACTIVE','INACTIVE','RETIRED'))
)
```

## suppliers

| Column | SQLite type | Required | Primary key | Default |
|---|---|---|---|---|
| `supplier_id` | TEXT | No | Yes | `-` |
| `name` | TEXT | Yes | No | `-` |
| `risk_tier` | TEXT | Yes | No | `-` |
| `country` | TEXT | Yes | No | `-` |
| `active` | INTEGER | Yes | No | `1` |

**Foreign keys**

- No declared foreign keys.

**Declared table constraints**

```sql
CREATE TABLE suppliers (
    supplier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    risk_tier TEXT NOT NULL CHECK (risk_tier IN ('LOW','MEDIUM','HIGH')),
    country TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
)
```

## 3. Relationship summary

Each foreign key represents a child-to-parent reference. Multiple child records may reference the same parent unless a uniqueness constraint restricts that relationship.

Lifecycle events use `entity_type` and `entity_id` as a polymorphic reference. No foreign key is declared for these fields.

## 4. Documentation limitations

- SQLite types describe storage affinity, not necessarily business units.
- Optionality is derived from schema nullability.
- Business-level relationships not enforced by foreign keys require application-level validation.
- The lifecycle event entity reference is not enforced by a database FK.

