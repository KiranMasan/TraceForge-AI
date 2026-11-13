# TraceForge AI
### Manufacturing Defect Traceability & Quality Intelligence

TraceForge AI is a manufacturing traceability and quality intelligence prototype designed to investigate defects across the complete production lifecycle.

It connects inspection results to production orders, process steps, machines, consumed material lots, suppliers, and corrective actions.

## Problem Statement

Manufacturing defects can originate from materials, suppliers, machines, or production processes. Investigating these issues requires connecting information distributed across multiple records.

TraceForge AI provides an integrated view of manufacturing data to help identify traceability gaps, investigate quality issues, validate data integrity, and track corrective actions.

## Key Features

- **End-to-end traceability:** Follow defects from inspection results to production orders, process steps, machines, material lots, and suppliers.
- **Production investigation:** Examine BOM requirements, material consumption, process history, and inspection outcomes.
- **Supplier quality analysis:** Investigate material lots and supplier-associated quality issues.
- **CAPA tracking:** Review corrective and preventive action status, verification, and closure history.
- **Data validation:** Check database integrity, material balances, BOM consumption, inspection quantities, defect relationships, and CAPA consistency.
- **Anomaly detection:** Detect deliberately introduced traceability and data-integrity anomalies using rule-based checks.
- **Interactive dashboard:** Explore manufacturing quality information through five Streamlit dashboard sections.

## Technology Stack

- Python 3.11
- SQLite
- Pandas
- NumPy
- Streamlit
- Plotly
- Pytest

## Project Structure

```text
TraceForge-AI/
├── app/
│   └── dashboard.py
├── data/
│   ├── generated/
│   └── ground_truth/
├── docs/
│   ├── architecture.md
│   └── data_dictionary.md
├── scripts/
│   ├── generate_data.py
│   ├── validate_data.py
│   ├── detect_anomalies.py
│   └── inspect_schema.py
├── src/
│   └── traceforge/
│       ├── schema.sql
│       ├── generator.py
│       ├── validation.py
│       └── anomaly_detector.py
├── tests/
│   ├── test_anomaly_detector.py
│   └── test_validation.py
├── requirements.txt
└── README.md
```

## Installation

Requirements: Python 3.11 or compatible version and pip.

Clone the repository:

```bash
git clone https://github.com/KiranMasan/TraceForge-AI.git
cd TraceForge-AI
```

Create and activate a virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Generate the Dataset

Generate the starter dataset:

```powershell
python scripts/generate_data.py --scale starter --seed 20261022
```

Generate the full dataset:

```powershell
python scripts/generate_data.py --scale full --seed 20261022
```

The generator uses a fixed random seed to support reproducible synthetic dataset generation.

## Validate the Dataset

```powershell
python scripts/validate_data.py --scale full
```

The validation engine checks database integrity and manufacturing relationships, reporting violations with examples.

## Run Anomaly Detection

```powershell
python scripts/detect_anomalies.py --scale full
```

The current detector uses rule-based checks against five deliberately constructed anomaly fixtures.

## Run Automated Tests

```powershell
pytest -v
```

## Launch the Dashboard

```powershell
streamlit run app/dashboard.py
```

Open the local URL displayed in the terminal, usually:

```text
http://localhost:8501
```

## Dashboard Sections

1. **Overview:** Manufacturing KPIs, production status, inspection results, defect severity, and CAPA status.
2. **Defect Traceability:** Investigate individual defects and their associated production and material records.
3. **Production Investigation:** Explore production orders, BOM requirements, material consumption, machines, and inspections.
4. **Supplier Quality:** Examine supplier and material-lot quality information.
5. **CAPA Management:** Review corrective action records and their lifecycle status.

## Full Dataset Summary

The generated full dataset contains:

| Entity | Records |
|---|---:|
| Suppliers | 50 |
| Products | 200 |
| BOM records | 400 |
| Material lots | 2,000 |
| Machines | 20 |
| Production orders | 5,000 |
| Material consumption records | 10,000 |
| Process steps | 10,000 |
| Inspection plans | 200 |
| Inspection results | 20,000 |
| Defects | 1,158 |
| Corrective actions | 1,158 |
| Lifecycle events | 1,158 |

## Verification Results

Latest local verification:

- **Automated tests:** 5 passed.
- **Full dataset validation:** Passed with zero reported errors.
- **Synthetic anomaly detection:** 5 of 5 injected anomaly fixtures detected.
- **Dashboard:** All five sections manually verified.
- **Database:** SQLite.

**Evaluation note:** Anomaly detection metrics are measured against five deliberately constructed synthetic test fixtures. They demonstrate detection coverage on these fixtures, not generalized performance on unseen manufacturing data.

## Documentation

- `docs/architecture.md` — System architecture and data flow.
- `docs/data_dictionary.md` — Database tables, columns, and relationships.

## Project Status

Working prototype featuring synthetic manufacturing data, SQLite persistence, rule-based validation, anomaly detection, and an interactive Streamlit dashboard.

## Repository

GitHub: https://github.com/KiranMasan/TraceForge-AI

## License

No open-source license has been added yet. All rights reserved by default unless a license is subsequently added.
