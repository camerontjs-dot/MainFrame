# Deterministic Tool & Execution Integrity Standard

**Operating standard for executable tools, integration bridges, and evaluation tests.** This workflow enforces that every script in `bin/` or `scripts/` physically executes the computation it claims, tests real operational behavior rather than tautological mocks, and never allows agents to simulate deterministic outputs in prose.

## Profile

| Field | Value |
|---|---|
| structural_type | workflow |
| owner_surface | `AGENTS.md` (item 10) + `HARNESS.md` (ADR-051) |
| related | `epistemic-standard.md`, `eval-methodology.md`, `lab-report.md`, `process-evaluation.md` |

---

## 1. Purpose & The Anti-Simulation Rule

LLMs naturally suffer from a **"Scaffold-as-Execution" bias**: they generate schemas, parsers, and data packets, treat the pipeline as complete, and then synthesize plausible-looking evaluation tables or verdicts in Markdown without ever executing the underlying engine.

This standard establishes the **Anti-Simulation Rule**:
> **Never simulate compute.** A tool must physically invoke the model, compiler, database, or evaluation engine it represents, or fail closed. An agent must never author an audit table, verification scorecard, or verdict claiming deterministic tool authority unless backed by a persistent execution receipt on disk.

---

## 2. The Three-Layer Tool Taxonomy

Every script, CLI command, and function in MainFrame must strictly belong to and be named after one of three layers:

```
┌────────────────────────────────────────────────────────┐
│ Layer 1: Data Transformer / Packet Builder             │
│   Prefix: parse-*, build-*, format-*, stage-*          │
│   Role:   Pure data transformation & serialization.    │
│   Rule:   MUST NOT be named 'audit', 'verify', or      │
│           'evaluate'. MUST NOT emit verdicts.          │
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Layer 2: Operational Engine Runner                     │
│   Prefix: run-*, audit-*, verify-*, execute-*          │
│   Role:   Physically executes the engine/model/DB.     │
│   Rule:   MUST fail closed if engine is unavailable.   │
│           MUST write a persistent trace receipt.       │
└────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ Layer 3: Agent Qualitative Judgment                    │
│   Prefix: synthesize-*, review-*, appraise-*           │
│   Role:   LLM reasoning, contextual trade-offs.        │
│   Rule:   MUST be labeled 'evaluator: agent_llm'.      │
│           MUST NOT claim deterministic tool authority. │
└────────────────────────────────────────────────────────┘
```

### Naming & Responsibility Rules:
1. **Transformers (`build-*`, `format-*`, `parse-*`)**:
   - Only transforms inputs (e.g. Markdown → JSON request packet).
   - Must document clearly: *"Prepares packet for `<engine>`; does not execute `<engine>`."*
2. **Runners (`run-*`, `audit-*`, `verify-*`)**:
   - Ingests the packet, executes the deterministic engine (e.g. `claim_audit_lab`, PyTorch model, SQLite query, external subprocess), and writes output traces.
   - Must import or execute the real engine binary.
3. **Agent Heuristics (`synthesize-*`, `appraise-*`)**:
   - Contextual synthesis that cannot be evaluated deterministically.
   - Must be transparently attributed to LLM judgment.

---

## 3. The Fail-Closed Boundary

When a runner depends on external engines, local models, or environment packages (e.g. CAL, spaCy, PyTorch, Ollama, MLX, SQLite):

1. **Preflight Dependency Check**: Check that the engine binary, model weights, or Python package are importable and healthy before processing.
2. **No Mock Fallbacks in Production**: If the engine is missing or unreachable, the runner must exit with a non-zero status and print an explicit remediation message (e.g., `EngineUnavailableError: CAL v1 engine dependencies missing in environment`).
3. **Never Fallback to Agent Simulation**: Do not catch engine failure and replace it with a simulated result or blank "pass" object.

### 3.1 Degraded Runtimes, Exit Codes, and Escape-Valve Contracts (ADR-052)

Complex systems run as broken systems (Cook 1998). Software and CLI tools must maintain resilience and clear envelope visibility when running in degraded environments:

1. **Standard Exit Code Contract**:
   - `0`: Clean execution, zero policy violations / verification passed.
   - `1`: Operational success, but verification findings or lint/contract errors detected (actionable findings).
   - `2`: Tool crash, preflight failure, missing dependency, or unhandled exception (tool did not run cleanly; do not read as a verification result).
2. **Escape-Valve Contract for Quality Gates**:
   - Every gate validator (e.g., `bin/capture-validate`, `01_ingest/minion.py`, `bin/prep-ingest`) must provide structured, valid escape routes for partial or uncertain data (e.g., `type: hypothesis`, `status: queued`, `needs-audit`).
   - Rigid gates that lack escape valves create perverse incentives at the sharp end, forcing agents to fabricate metadata to satisfy the gate. A documented hypothesis or pending item is always superior to an invented source.
3. **Edge-of-the-Envelope Telemetry**:
   - When tools operate in degraded mode (e.g., daemon offline fallback, cached vector lookup, context truncation), the runner must write explicit diagnostic telemetry into the persistent receipt (`degraded: true`, `fallback_used: "local_sqlite"`, `boundary_warning: "token compaction near limit"`).

---

## 4. Falsification & Adversarial Test Discipline

A test suite that only tests positive happy paths or asserts against internal dictionary keys is **tautological**—it proves the code can run its own lines, not that it correctly validates reality.

Every test file under `tests/` for tools or evaluation bridges must implement at least **two falsification controls**:

### Control A: The Disconnection / Engine Failure Test
* Mock or simulate the backend engine being absent, raising an error, or timing out.
* **Assertion**: The tool must raise an exception or exit non-zero. It must **not** return a success code or partial fake verdict.

### Control B: The Adversarial / Contradictory Input Test
* Feed the tool deliberately false data (e.g. invalid DOI, contradicted claim, ungrounded passage).
* **Assertion**: The tool must output a negative verdict (`contradicted`, `insufficient`, `rejected`, or exit non-zero). If it returns `supported` or `ok`, the test fails.

---

## 5. The "Receipt or It Didn't Happen" Standard

To prevent agents from hallucinating evaluation results in summaries:

1. **Persistent Trace Files**: Every runner must write its output to disk under `outputs/` or `20_live/` (e.g. `<timestamp>-<target>-trace.json`).
2. **Mandatory Receipt Fields**:
   - `run_id` / `timestamp`
   - `engine_version` / `rules_version`
   - `input_hash` (SHA256 of source file/packet)
   - `verdicts` / `scores` (raw numbers, not summarized prose)
3. **Citation in Reports**: Any agent outputting an "Audit Table" or "Verification Scorecard" in a note or PR must include:
   ```markdown
   **Verification Receipt:** `outputs/cal-trials/2026-08-21-report-trace.json` (SHA256: `a1b2c3...`)
   ```

---

## 6. Authoring Checklist for New Scripts & Tests

Before committing any new script in `bin/` or `scripts/`, verify:

- [ ] **1. Taxonomy Alignment:** Is the tool correctly named as a Transformer (`build-*`) or Runner (`run-*`/`audit-*`)?
- [ ] **2. Engine Invocation:** Does the runner actually import/execute the backend engine, or does it stop at JSON serialization?
- [ ] **3. Fail-Closed Check:** Does it exit non-zero if the engine is missing or misconfigured?
- [ ] **4. Exit Code Contract:** Does it adhere to the `0` (pass) / `1` (findings) / `2` (crash) exit code contract?
- [ ] **5. Escape Valve Support:** If this tool gates workflow or metadata, does it support valid intermediate states (`type: hypothesis`, `status: queued`) without forcing fabricated values?
- [ ] **6. Receipt Generation:** Does execution leave a deterministic, hashed trace file on disk?
- [ ] **7. Falsification Test in `tests/`:** Is there a test asserting that invalid/contradictory input produces a failure verdict?
