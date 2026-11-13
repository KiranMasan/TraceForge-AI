# TraceForge AI — Engineering Assumptions, Design Decisions and Limitations

## 1. Overview

TraceForge AI is a manufacturing traceability and quality intelligence prototype designed to connect manufacturing records across the production lifecycle.

This document explains the assumptions, engineering decisions, validation approach, known limitations, and potential future improvements.

The intention is to make the system's behavior understandable, reproducible, and technically reviewable.

## 2. Business and Domain Assumptions

### 2.1 Manufacturing Data

- Manufacturing records are generated synthetically for demonstration and evaluation.
- Each entity has a deterministic identifier.
- Dependent records reference valid parent entities in the normal baseline dataset.
- Deliberately injected anomalies are identified using separate ground-truth labels.
- Derived values are calculated from source records wherever implemented.

### 2.2 Traceability

A manufacturing defect may be associated with:

- An inspection result.
- A production order.
- A production process step.
- A machine.
- A consumed material lot.
- A supplier.
- A corrective action.

Traceability depends on valid relationships between these entities. Missing or invalid relationships must be reported rather than silently assumed.

### 2.3 CAPA Business Rules

- Corrective actions follow defined lifecycle transitions.
- State changes are recorded as explicit lifecycle events.
- A CAPA cannot be closed without successful verification.
- Verification evidence must be linked to the relevant CAPA and manufacturing records.
- Inspection verification must use post-implementation evidence for the same product.

### 2.4 AI Investigation

- SQLite is the source of truth for manufacturing records.
- The Copilot retrieves relevant database evidence before generating explanations.
- Ollama is used for local language-model inference.
- AI-generated hypotheses are not automatically accepted as confirmed root causes.
- Manufacturing decisions require human review.

## 3. Architecture and Technology Decisions

| Component | Decision | Engineering rationale |
|---|---|---|
| Programming language | Python 3.11 | Suitable for data engineering, validation, and application development |
| Database | SQLite | Lightweight, portable, and locally runnable |
| Data processing | Pandas and NumPy | Efficient synthetic data generation and analysis |
| Dashboard | Streamlit | Rapid development of an interactive engineering interface |
| Visualization | Plotly | Interactive manufacturing quality analytics |
| AI inference | Ollama | Local model execution without depending on a hosted LLM API |
| Testing | Pytest | Repeatable verification of business logic |
| Data validation | Deterministic rules | Explainable and reproducible validation decisions |

The architecture prioritizes local execution, understandable business logic, reproducibility, and lightweight dependencies.

## 4. Synthetic Data Generation Decisions

The full dataset uses a fixed random seed:

`20261022`

The generated dataset includes:

| Entity | Records |
|---|---:|
| Suppliers | 50 |
| Products | 200 |
| BOM records | 400 |
| Material lots | 2,000 |
| Machines | 20 |
| Production orders | 5,000 |
| Material consumption | 10,000 |
| Process steps | 10,000 |
| Inspection plans | 200 |
| Inspection results | 20,000 |
| Defects | 1,158 |
| Corrective actions | 1,158 |
| Lifecycle events | 1,158 |

**Total: 51,344 records.**

The generator supports starter and full dataset scales using shared generation logic.

The dataset is synthetic and should not be interpreted as actual factory performance data.

## 5. Anomaly Detection Decisions

The anomaly detector uses deterministic, rule-based validation.

The five deliberately injected anomaly categories are:

1. `NONEXISTENT_LOT_REFERENCE`
2. `BOM_MATERIAL_NOT_CONSUMED`
3. `CAPA_CLOSED_BEFORE_VERIFICATION`
4. `DEFECTS_EXCEED_INSPECTED_QUANTITY`
5. `BROKEN_TRACEABILITY`

The detector checks these scenarios against the generated manufacturing records.

The reported result is five out of five injected fixtures detected.

This demonstrates detection coverage on the designed fixtures. It does not establish generalization to unseen production data or represent a statistically meaningful real-world accuracy score.

## 6. CAPA Lifecycle and Verification Design

The CAPA lifecycle contains:

`OPEN → CONTAINMENT → INVESTIGATING → IMPLEMENTED → VERIFIED → CLOSED`

Lifecycle transitions are stored as explicit records instead of overwriting historical events.

The verification workflow includes:

1. Confirming that a corrective action has been implemented.
2. Recording relevant verification evidence.
3. Validating relationships between the CAPA and supporting manufacturing records.
4. Checking approved process specifications for process-measurement evidence.
5. Requiring passing, post-implementation inspection evidence for the same product before verification.
6. Allowing closure only after successful verification.

The service layer enforces the implemented business rules and has automated tests covering lifecycle and evidence validation.

## 7. TraceForge Copilot Design

TraceForge Copilot combines deterministic database retrieval with local LLM-generated explanations.

Its workflow is:

`Question → Evidence Retrieval → Context Preparation → Local LLM → Investigation Response`

Key design decisions:

- Manufacturing evidence is retrieved from SQLite.
- The LLM receives relevant evidence rather than being treated as a database.
- The local model is `llama3.2:3b`.
- Evidence references are included to support investigation.
- Facts and hypotheses should be distinguished in generated responses.

This is database-grounded evidence retrieval. It is not a vector database or embedding-based semantic retrieval implementation.

## 8. Validation and Testing

Latest reported local verification:

| Verification | Result |
|---|---|
| Automated tests | 14 passed |
| Full dataset validation | Passed, zero reported errors |
| Injected anomaly fixtures | 5 of 5 detected |
| CAPA lifecycle tests | Passed |
| CAPA verification tests | Passed |
| Database migration | Tested on temporary database copy |
| Dashboard | Sections manually reviewed |

The migration was tested against a temporary database copy to avoid unnecessarily modifying the original working database.

These results describe the local verification performed for the prototype. They do not constitute production certification or independent external testing.

## 9. Known Limitations

### 9.1 Synthetic Dataset

- The dataset does not represent real factory operations.
- Synthetic distributions may not cover all manufacturing conditions.
- Real-world supplier, machine, and process behavior may be more complex.

### 9.2 Database and Enterprise Integration

- SQLite is appropriate for this prototype but may not be sufficient for a high-concurrency enterprise deployment.
- Live ERP, MES, SCADA, and industrial machine integrations have not been implemented.
- Production authentication, authorization, and multi-user operational controls are outside the current prototype scope.

### 9.3 Anomaly Detection

- The current detector is rule-based.
- Only five deliberately constructed anomaly fixtures are included in the reported evaluation.
- Performance on unseen manufacturing anomalies has not been established.
- Additional rules and independent evaluation datasets are required for broader assessment.

### 9.4 CAPA Management

- CAPA lifecycle and verification logic are implemented in the service layer.
- The dashboard currently provides read-only CAPA monitoring rather than a complete interactive workflow interface.
- Additional evidence types and industry-specific verification policies may be required for real deployments.
- The synthetic baseline contains snapshot lifecycle records rather than a complete historical audit trail for every CAPA.

### 9.5 AI Copilot

- Copilot requires Ollama and an available local model.
- Response quality depends on the model and retrieved evidence.
- Language models can generate incorrect interpretations.
- Semantic vector search and embedding-based retrieval are not currently implemented.
- Human review is required before acting on AI-generated recommendations.

### 9.6 Operational Deployment

- The project is a working prototype rather than a production-ready manufacturing platform.
- High availability, disaster recovery, centralized monitoring, and deployment automation are not fully implemented.
- Performance under large-scale concurrent workloads has not been evaluated.

## 10. Security and Data Handling

- The project uses synthetic manufacturing records.
- No confidential factory records are required for the demonstration.
- Local configuration and credentials should not be committed to the public repository.
- Ollama is configured for local inference.
- The repository should be reviewed for accidental secrets and sensitive files before submission.

## 11. Future Improvements

Potential future improvements include:

1. Integration with real ERP and MES platforms.
2. Migration to a production-grade relational database.
3. Role-based authentication and authorization.
4. Expanded anomaly scenarios and independent evaluation datasets.
5. A complete interactive CAPA management interface.
6. More advanced evidence retrieval and semantic search.
7. Process-specific verification policies.
8. Operational monitoring and deployment automation.
9. Performance and scalability testing.

These are proposed improvements, not claims about currently implemented functionality.

## 12. Conclusion

TraceForge AI demonstrates an integrated approach to manufacturing traceability and quality intelligence.

The prototype combines deterministic synthetic data generation, relational data modeling, manufacturing traceability, rule-based anomaly detection, CAPA lifecycle management, verification evidence, and local AI-assisted investigation.

The engineering approach emphasizes:

- Explainable business rules.
- Traceable manufacturing evidence.
- Explicit lifecycle history.
- Reproducible synthetic datasets.
- Automated validation.
- Transparent AI usage.
- Clearly documented limitations.

The project is intended to demonstrate practical engineering judgment and a foundation for further development in manufacturing quality intelligence.