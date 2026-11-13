
-- Migration 010: Process specifications and CAPA verification evidence

CREATE TABLE IF NOT EXISTS process_specifications (
    specification_id TEXT PRIMARY KEY,
    sku TEXT NOT NULL REFERENCES products(sku),
    machine_id TEXT NOT NULL REFERENCES machines(machine_id),
    process_name TEXT NOT NULL,
    version TEXT NOT NULL,

    temperature_min REAL,
    temperature_max REAL,
    pressure_min REAL,
    pressure_max REAL,

    effective_from TEXT NOT NULL,
    effective_to TEXT,

    approved_by TEXT NOT NULL,
    approval_reference TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        temperature_min IS NULL
        OR temperature_max IS NULL
        OR temperature_min <= temperature_max
    ),
    CHECK (
        pressure_min IS NULL
        OR pressure_max IS NULL
        OR pressure_min <= pressure_max
    ),
    CHECK (
        temperature_min IS NOT NULL
        OR temperature_max IS NOT NULL
        OR pressure_min IS NOT NULL
        OR pressure_max IS NOT NULL
    ),
    CHECK (
        effective_to IS NULL
        OR effective_to >= effective_from
    ),

    UNIQUE (sku, machine_id, process_name, version)
);

CREATE INDEX IF NOT EXISTS idx_process_spec_lookup
ON process_specifications (
    sku, machine_id, process_name, effective_from
);

CREATE TABLE IF NOT EXISTS capa_verification_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,

    capa_id TEXT NOT NULL
        REFERENCES corrective_actions(capa_id),

    evidence_type TEXT NOT NULL
        CHECK (evidence_type IN (
            'PROCESS_MEASUREMENT',
            'INSPECTION',
            'DOCUMENT',
            'OTHER'
        )),

    process_step_id TEXT REFERENCES process_steps(step_id),
    inspection_id TEXT REFERENCES inspection_results(inspection_id),

    specification_id TEXT
        REFERENCES process_specifications(specification_id),

    evidence_reference TEXT NOT NULL,

    temperature REAL,
    pressure REAL,

    verification_result TEXT NOT NULL
        CHECK (verification_result IN (
            'PASS', 'FAIL', 'INCONCLUSIVE'
        )),

    evidence_notes TEXT NOT NULL,
    recorded_by TEXT NOT NULL,
    recorded_at TEXT NOT NULL,

    CHECK (
        evidence_type != 'PROCESS_MEASUREMENT'
        OR (
            process_step_id IS NOT NULL
            AND specification_id IS NOT NULL
        )
    ),

    CHECK (
        evidence_type != 'INSPECTION'
        OR inspection_id IS NOT NULL
    ),

    UNIQUE (capa_id, evidence_reference)
);

CREATE INDEX IF NOT EXISTS idx_capa_evidence
ON capa_verification_evidence(capa_id);

CREATE INDEX IF NOT EXISTS idx_evidence_process_step
ON capa_verification_evidence(process_step_id);

CREATE INDEX IF NOT EXISTS idx_evidence_inspection
ON capa_verification_evidence(inspection_id);
