# System Integrity Audit Workflow

Use this workflow to audit and review system architectures, software workflows, or AI data pipelines from a data-integrity perspective. This protocol evaluates how reliably a system captures evidence, traces decisions, maintains rule versioning, and handles data preservation.

## Related docs

| Context / Template | Path |
|:---|:---|
| Meeting lifecycle | [boardy-meeting-lifecycle.md](boardy-meeting-lifecycle.md) |
| Website audit | [website-audit.md](website-audit.md) |
| Epistemic standard | [epistemic-standard.md](epistemic-standard.md) |

---

## 1. Scope & Calibration Boundary

Every review must start with a clear definition of bounds to manage liability and establish peer-to-peer collaboration:
- **Data-Integrity Focus:** Review is strictly limited to how data flows, where it is recorded, how it is modified, and how decisions are reconstructed.
- **Not a Legal/Compliance Opinion:** State clearly that this is an architectural peer review, not a formal legal counsel, privacy audit (e.g. GDPR/CCPA certification), or regulatory inspection.
- **Execution vs. Documentation:** Clarify whether the review is based on written documentation/diagrams alone or verified via a live trace.

---

## 2. Step-by-Step Audit Procedure

Follow this sequence when auditing a client's system architecture:

### Step 2.1: Map the Anatomy of the System
Identify the core components of the target system:
1. **Raw Inputs:** The original user data, uploads, API requests, or events.
2. **Transient/Processing Layer:** Intermediate APIs, transcription services, worker queues, LLM parsers, or temporary databases.
3. **Derived Outputs:** Summaries, dashboards, notifications, or reports generated for the user.
4. **Decision Gates:** Where human review or approval blocks automated downstream actions.

### Step 2.2: Identify the Survival Boundary
Determine the relationship between raw inputs and derived outputs:
- **The Survival Test:** If the raw input is deleted (e.g., for data minimization or privacy), does the system preserve enough structured evidence to independently reconstruct and defend the output?
- If the original evidence is deleted and the client only retains scores/verdicts, highlight that the retained records cannot be audited or replayed.

### Step 2.3: Execute the R1–R8 Checklist
Evaluate the system against the **R1–R8 System Integrity Checklist** (Section 3). For each point:
- Mark as **PASS** if the system meets the condition.
- Mark as **GAP** if the system relies on unverified assertions or manual workflows.
- Detail the exact risk and remediation for each GAP.

### Step 2.4: Define the Synthetic Walkthrough
Design a concrete "verification trace" to test the system's actual behavior on a single synthetic record. Outlining this walkthrough forces the client to move from *assertions of design* to *operational proof*.

### Step 2.5: Draft the Review
Package the findings into the standard audit report layout (Section 4). Maintain a peer-to-peer, collaborative, and constructive tone.

---

## 3. The R1–R8 System Integrity Checklist

Use this standard checklist to evaluate the robustness of any data pipeline or decision-making system.

| Code | Principle | Audit Question | Pass Condition |
| :--- | :--- | :--- | :--- |
| **R1** | **Raw Source Capture** | Can we identify the authoritative, raw source records that triggered the system run? | The raw inputs (e.g. raw transcripts, uploaded files, API payloads) are preserved with unique IDs, hashes, and timestamps. |
| **R2** | **Logic/Rule Versioning** | Can we recover the exact rule schema, prompt template, model parameters, or code commit in effect at the time of execution? | The run log records the exact version identifier or snapshot of the governing logic. |
| **R3** | **Run Initialization Log** | Is the start of the workflow recorded immediately in a non-repudiable log? | The database writes a run entry at the initialization timestamp before downstream processing. |
| **R4** | **Sequenced Execution Path** | Does the logic trace a strict, ordered progression of validation nodes? | The execution path or trace shows that prerequisites were satisfied before proceeding. |
| **R5** | **Outcome-to-Source Traceability** | Is every rating, flag, or verdict dimension supported by specific, attributable evidence? | The system output links specific claims back to segments of the source data or database states. |
| **R6** | **Controlled System Overrides** | Are exceptions, manual corrections, or rule overrides recorded transparently? | Adjustments to system state are logged as separate, signed events (`PATCH` transactions) rather than silently overwriting the original output. |
| **R7** | **Attributable Approval Gates** | Is human oversight a hard gate (rather than a retrospective override), and is it signed by a verified account? | The workflow requires a named human supervisor to confirm the verdict before triggering downstream automation. |
| **R8** | **Exportable Evidence Package** | Does the final output package contain verifiable links or hashes of all run elements? | The delivered report or API packet contains cryptographic hashes of the raw input, the active policy version, the run logs, and the approval events. |

---

## 4. Audit Report Template

When drafting the final deliverable for a client, copy and use the format below.

```markdown
# System Integrity & Data-Flow Review: [System Name]

*Prepared by Cameron Sanderson*
*Date: [Date]*

---

## Scope & Boundaries
I reviewed the [System Name] architecture and data-flow specifications from a data-integrity and decision-reconstruction perspective.

This review covers system architecture, record linkage, and data-preservation design. It is not a legal opinion, a privacy assessment, or a formal compliance certification. The findings below are based on the provided technical package and should be verified on a live system trace.

---

## Start Here: The Core Survival Test
[Identify the main point of vulnerability in the system. Typically, this is whether the raw source data survives deletion/minimization, and what the retained summaries actually prove if audited.]

---

## Architectural Findings

### 1. [Finding Heading - e.g., Logic Versioning Gaps]
[Analyze what is currently happening vs. what is required. Reference R2 or other R-principles.]

### 2. [Finding Heading - e.g., Audit Trail Attributability]
[Analyze the storage of audit logs. Highlight if logs are stored in soft formats like spreadsheets or databases without write-once protection.]

### 3. [Finding Heading - e.g., Human-in-the-Loop Boundaries]
[Detail whether human review is a hard gate blocking automation, or merely a retrospective override.]

---

## Reconstruction Trace Checklist
During the upcoming walkthrough, we should trace a single synthetic execution to verify the following parameters:

- [ ] **Authoritative Source:** Verify what remains in client and system storage post-deletion.
- [ ] **Logic Versioning:** Trace one automated output back to the exact rule schema, prompt file, and model version.
- [ ] **Logging & Error Capture:** Force a processing error and verify that it triggers an alert and logs a failure rather than reporting false success.
- [ ] **Access & Credentials:** Confirm the actual permissions of the system's service accounts and verify that they match the stated access control boundaries.
- [ ] **Human Sign-Off:** Confirm that downstream automation is blocked until a user approval signature is written to the audit log.

---

## Summary Assessment
[Summarize the recommendations. Emphasize separating data minimization (deleting transient files) from decision preservation (keeping audit trails, hashes, and human sign-off records intact).]
```
