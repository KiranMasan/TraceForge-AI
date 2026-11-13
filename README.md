# TraceForge AI
### End-to-End Manufacturing Traceability & Quality Intelligence

TraceForge AI is a manufacturing traceability and quality intelligence prototype designed to investigate defects across the complete production lifecycle.

It connects inspection results to production orders, process steps, machines, consumed material lots, suppliers, and corrective actions. It combines deterministic data validation, rule-based anomaly detection, CAPA lifecycle management, and an AI-powered investigation assistant.

## Problem Statement

Manufacturing defects can originate from materials, suppliers, machines, or production processes. Investigating these issues requires connecting information distributed across multiple records.

TraceForge AI provides an integrated platform to help manufacturing and quality teams:

- Trace defects through the production and supply chain.
- Investigate material, supplier, and process-related quality issues.
- Identify data-integrity and traceability anomalies.
- Monitor corrective and preventive actions.
- Validate corrective-action verification evidence.
- Explore manufacturing evidence using an AI-powered assistant.

## Key Features

### 1. End-to-End Defect Traceability
- Trace defects from inspection results to production orders.
- Identify associated process steps and machines.
- Follow material consumption to material lots and suppliers.
- Connect defects to their corrective actions.
- Investigate upstream and downstream relationships.

### 2. Production Investigation
- Examine bill of materials (BOM) requirements.
- Review material consumption records.
- Inspect production process history.
- Analyze inspection results and defect records.
- Investigate production-level quality issues.

### 3. Supplier Quality Analysis
- Explore supplier and material-lot relationships.
- Investigate supplier-associated defects.
- Review material traceability and quality information.

### 4. CAPA Lifecycle Management
- Manage corrective and preventive action lifecycle states.
- Record lifecycle transitions as explicit audit events.
- Maintain chronological CAPA history.
- Track implementation and verification evidence.
- Enforce verification before CAPA closure.

Supported lifecycle states:

`OPEN → CONTAINMENT → INVESTIGATING → IMPLEMENTED → VERIFIED → CLOSED`

### 5. CAPA Verification
- Record inspection and process-measurement evidence.
- Associate evidence with approved process specifications.
- Validate product, machine, process, and specification relationships.
- Check post-implementation inspection evidence.
- Prevent verification and closure when required evidence is missing or invalid.

### 6. TraceForge Copilot
- AI-powered manufacturing investigation assistant.
- Uses local Ollama models for response generation.
- Retrieves relevant evidence directly from the SQLite database.
- Supports defect, production-order, product, supplier, and material-lot investigations.
- Provides evidence-grounded explanations and source references.
- Separates database-supported facts from potential hypotheses.

The Copilot uses database-grounded evidence retrieval. Ollama generates explanations from the retrieved evidence rather than independently determining manufacturing facts.

### 7. Data Validation and Anomaly Detection
- Validate primary-key uniqueness and foreign-key relationships.
- Check material balances and BOM consumption.
- Validate inspection quantities and defect relationships.
- Identify broken traceability relationships.
- Detect deliberately injected data-integrity anomalies.
- Preserve separate ground-truth labels for synthetic anomaly evaluation.

### 8. Interactive Dashboard
The Streamlit dashboard provides the following sections:

1. **Overview:** Manufacturing KPIs, production status, inspection results, defect severity, and CAPA metrics.
2. **Defect Traceability:** Investigate individual defects and associated production and material records.
3. **Production Investigation:** Explore production orders, BOM requirements, material consumption, machines, and inspections.
4. **Supplier Quality:** Examine supplier and material-lot quality information.
5. **CAPA Management:** Review corrective-action records and lifecycle status.
6. **TraceForge Copilot:** Ask manufacturing investigation questions using database-grounded evidence and local AI.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11 | Core application and business logic |
| SQLite | Manufacturing database and persistence |
| Pandas | Data processing and analysis |
| NumPy | Synthetic data generation |
| Streamlit | Interactive dashboard |
| Plotly | Data visualization |
| Ollama | Local LLM inference |
| Pytest | Automated testing |

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
│       ├── anomaly_detector.py
│       ├── capa_service.py
│       ├── copilot.py
│       ├── migrate.py
│       └── migrations/
│           └── 010_process_verification.sql
├── tests/
│   ├── test_anomaly_detector.py
│   ├── test_validation.py
│   └── test_capa_service.py
├── requirements.txt
└── README.md
```

## Installation

### Requirements

- Python 3.11 or compatible version.
- pip.
- Ollama (required for AI Copilot functionality).

### Clone the Repository

```bash
git clone https://github.com/KiranMasan/TraceForge-AI.git
cd TraceForge-AI
```

### Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install Dependencies

```powershell
pip install -r requirements.txt
```

## Generate the Synthetic Dataset

TraceForge AI supports starter and full dataset generation using a deterministic random seed.

### Starter Dataset

```powershell
python scripts/generate_data.py --scale starter --seed 20261022
```

### Full Dataset

```powershell
python scripts/generate_data.py --scale full --seed 20261022
```

The fixed seed supports reproducible synthetic data generation.

## Validate the Dataset

```powershell
python scripts/validate_data.py --scale full
```

The validation engine checks database integrity and manufacturing relationships and reports violations with examples.

## Run Anomaly Detection

```powershell
python scripts/detect_anomalies.py --scale full
```

The rule-based detector checks for deliberately constructed manufacturing data anomalies.

The five injected anomaly categories include:

1. NONEXISTENT_LOT_REFERENCE
2. BOM_MATERIAL_NOT_CONSUMED
3. CAPA_CLOSED_BEFORE_VERIFICATION
4. DEFECTS_EXCEED_INSPECTED_QUANTITY
5. BROKEN_TRACEABILITY

## Run Automated Tests

```powershell
pytest -v
```

The test suite covers:

- Anomaly detection.
- Database and manufacturing data validation.
- CAPA lifecycle transitions.
- CAPA transition rejection rules.
- Chronological lifecycle history.
- Verification evidence requirements.
- Inspection evidence and product consistency.
- Duplicate evidence-reference handling.

## Run the Dashboard

```powershell
streamlit run app/dashboard.py
```

Open the local URL displayed in the terminal, usually:

```text
http://localhost:8501
```

## Configure TraceForge Copilot

TraceForge Copilot uses Ollama to run a local language model.

### Install Ollama

Download Ollama from:

https://ollama.com/

### Download the Recommended Model

```powershell
ollama pull llama3.2:3b
```

### Start Ollama

```powershell
ollama serve
```

If Ollama is already running in the background, you do not need to start it again.

Launch the Streamlit dashboard and open the **TraceForge Copilot** section.

The Copilot retrieves manufacturing evidence from SQLite and uses the local model to generate an investigation response.

AI responses should be interpreted alongside their cited database evidence. Potential causes and recommendations are not automatically verified manufacturing facts.

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

**Total: 51,344 records**

## CAPA Verification Workflow

TraceForge AI implements evidence-backed CAPA verification.

The workflow includes:

1. Record the corrective action and root cause.
2. Implement the corrective action.
3. Record relevant verification evidence.
4. Validate evidence against the associated manufacturing records and specifications.
5. Verify the CAPA only when the required passing, post-implementation inspection evidence is available.
6. Close the CAPA after successful verification.

Lifecycle changes are stored as explicit events to preserve audit history.

The verification service includes checks for product consistency, inspection-plan relationships, evidence references, and approved process specifications.

## Verification Results

Latest local verification:

- **Automated tests:** 14 passed.
- **Full dataset validation:** Passed with zero reported errors.
- **Synthetic anomaly detection:** 5 of 5 injected anomaly fixtures detected.
- **CAPA lifecycle:** Transition and audit-history tests passed.
- **CAPA verification:** Verification evidence and validation tests passed.
- **Database migration:** Migration tested on a temporary database copy.
- **Dashboard:** Six sections implemented and manually reviewed.

**Evaluation note:** Anomaly detection results are based on five deliberately constructed synthetic fixtures. They demonstrate detection coverage on those fixtures, not generalized performance on unseen manufacturing data.

The full-dataset validation result and the anomaly fixture evaluation measure different aspects of the system.

## Reproducibility

The synthetic dataset generator uses a fixed seed:

`20261022`

The starter and full dataset scales use the same generator logic with different volume parameters.

The generated data is synthetic and intended for demonstration, testing, and evaluation.

## Documentation

- `docs/architecture.md` — System architecture and data flow.
- `docs/data_dictionary.md` — Database entities, fields, and relationships.

## Project Status

**Working prototype.**

TraceForge AI demonstrates an integrated manufacturing traceability and quality intelligence workflow with:

- Deterministic synthetic manufacturing data.
- SQLite persistence.
- End-to-end defect traceability.
- Rule-based data validation and anomaly detection.
- CAPA lifecycle management and verification evidence.
- Local Ollama-powered manufacturing investigation.
- Interactive Streamlit dashboard.
- Automated tests.

## Repository

GitHub:

https://github.com/KiranMasan/TraceForge-AI

## License

No open-source license has been added. All rights are reserved by default unless a license is subsequently added.