# TraceForge AI — AI Prompt History

## 1. Purpose

This document records the use of AI tools during the development of TraceForge AI.

AI assistance was used to accelerate technical research, architecture planning, implementation guidance, debugging, testing, and documentation.

The developer remains responsible for understanding the implementation, reviewing suggestions, making engineering decisions, and validating the final system.

## 2. AI Tools Used

| Tool | Usage |
|---|---|
| ChatGPT | Architecture planning, Python implementation guidance, debugging, testing strategy, code review assistance, and documentation |
| VS Code Agent / Codex | Include implementation and debugging tasks if used |
| Ollama — llama3.2:3b | Local language-model inference within TraceForge Copilot |

Other AI coding tools should be listed here only if they were actually used.

## 3. Development Areas Where AI Assistance Was Used

### 3.1 System Architecture and Database Design

**Development tasks:**
- Designing the manufacturing traceability workflow.
- Identifying manufacturing entities and relationships.
- Planning SQLite database tables and foreign-key relationships.
- Structuring the Python project.

**Prompt record:** Add the original prompts used for these tasks from the relevant AI conversation history.

### 3.2 Synthetic Data Generation

**Development tasks:**
- Generating deterministic manufacturing master data.
- Creating dependent production and inspection records.
- Maintaining consistent identifiers and relationships.
- Designing deliberate anomaly scenarios.
- Separating synthetic ground-truth labels from ordinary input data.

**Prompt record:** Add the original prompts used for these tasks.

### 3.3 Data Validation and Anomaly Detection

**Development tasks:**
- Implementing database integrity checks.
- Validating manufacturing relationships and material consumption.
- Detecting deliberately injected traceability anomalies.
- Evaluating the detector against known synthetic fixtures.

**Prompt record:** Add the original prompts used for these tasks.

### 3.4 CAPA Lifecycle and Verification

**Development tasks:**
- Designing CAPA lifecycle transitions.
- Recording state changes as explicit audit events.
- Implementing evidence-backed verification.
- Enforcing verification before CAPA closure.
- Testing invalid transitions and evidence relationships.

**Prompt record:** Add the original prompts used for these tasks.

### 3.5 TraceForge Copilot

**Development tasks:**
- Designing database-grounded evidence retrieval.
- Integrating a locally hosted Ollama model.
- Generating manufacturing investigation explanations.
- Distinguishing retrieved facts from possible explanations.

**Prompt record:** Add the original prompts used for these tasks.

### 3.6 Debugging and Testing

**Development tasks:**
- Investigating Python and SQLite errors.
- Correcting implementation issues.
- Resolving automated test failures.
- Validating migrations and application behavior.

**Prompt record:** Add the original debugging and testing prompts.

### 3.7 Documentation and Submission Preparation

**Development tasks:**
- Preparing project documentation.
- Explaining design decisions and limitations.
- Reviewing installation and execution instructions.

**Prompt record:** Add the original prompts used for these tasks.

## 4. Original Prompt Archive

The following section is the prompt archive. Add the actual prompts submitted to each AI tool, preserving their original wording.

### ChatGPT

| No. | Development stage | Original prompt |
|---|---|---|
| 1 | Architecture | Paste original prompt |
| 2 | Database design | Paste original prompt |
| 3 | Synthetic data generation | Paste original prompt |
| 4 | Validation | Paste original prompt |
| 5 | Anomaly detection | Paste original prompt |
| 6 | CAPA implementation | Paste original prompt |
| 7 | CAPA verification | Paste original prompt |
| 8 | Copilot implementation | Paste original prompt |
| 9 | Debugging and testing | Paste original prompts |
| 10 | Documentation | Paste original prompts |

### VS Code Agent / Codex

Include the original prompts from the coding-agent sessions used to implement or modify the project.

| No. | Development stage | Original prompt |
|---|---|---|
| 1 | Implementation | Paste original prompt |
| 2 | Debugging | Paste original prompt |
| 3 | Testing | Paste original prompt |

### Other AI Tools

Add a separate prompt archive for each additional AI tool actually used.

## 5. Runtime AI Usage

TraceForge Copilot uses Ollama with the locally hosted `llama3.2:3b` model.

Its runtime workflow is:

1. Receive a manufacturing investigation question.
2. Retrieve relevant records from the SQLite database.
3. Prepare an evidence-grounded prompt.
4. Send the prompt to the local Ollama model.
5. Generate an investigation explanation.
6. Present the answer with supporting source references.

The runtime prompt and evidence-retrieval implementation are maintained in:

`src/traceforge/copilot.py`

Runtime prompts generated by the application are separate from development prompts submitted to AI coding assistants.

## 6. Human Review and Validation

AI assistance does not replace engineering verification.

The developer reviewed the implementation using:

- Database integrity checks.
- Foreign-key and relationship validation.
- Synthetic anomaly fixture evaluation.
- CAPA lifecycle and verification tests.
- Automated test execution.
- Database migration checks.
- Manual dashboard verification.
- Local execution of the AI Copilot.

The database remains the source of truth for manufacturing evidence. AI-generated explanations are subject to human review.

## 7. Prompt History Completeness and Transparency

The complete original prompts should be recovered from the available conversation histories and coding-agent sessions.

Where a tool does not provide access to its complete historical prompts, the limitation must be explicitly disclosed.

The task descriptions in this document are an index of AI-assisted development activities. They must not be represented as verbatim original prompts.

No missing prompts have been intentionally fabricated.

## 8. Developer Responsibility

The developer is responsible for the final implementation, understanding its dependencies and design decisions, validating the system, and explaining its limitations during technical evaluation.