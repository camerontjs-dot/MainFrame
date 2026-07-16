# MainFrame Harness Operating Contract

A **harness** is the environment around a model: instructions, state, verification, scope, and session lifecycle. It is not the model brand. The harness makes output **reliable**; the model makes output **possible**.

This file is the public harness policy summary for MainFrame Stage 1.

## Three documentation layers

| Layer | Typical location | Trust |
| --- | --- | --- |
| **Patterns** | Durable notes under `10_knowledge/` (private corpora) | Durable knowledge |
| **Program / status** | Project logs and plans under `30_projects/` (local) | Project status |
| **Contract** | This file + root `AGENTS.md` | Operating policy |

Do not treat retrieval hits or telemetry counters as proof of graduated capability.

## Planning, execution, verification

1. **Planning** — Frontier or human operators produce reviewed task packets when work is delegated. Unresolved design stays out of execution.
2. **Execution** — Local or cloud agents run inside declared scope. Run state goes to receipts, not silent mutation of the packet.
3. **Verification** — Prefer external deterministic checks (tests, linters, scope diff). Retrieval systems supply **context nominations only**, never verification.

## Deterministic work stays out of the model loop

Patch application, index generation, exact scripted rewrites, and `bin/*` minion passes run without a model unless a conflict requires judgment.

## Session lifecycle

- `bin/session-open` loads a fixed context order for a work session.
- `bin/session-close` reports and optionally applies end-of-session hygiene.

Exact hook wiring is environment-specific and may stay private.

## Promotion

Reusable lessons move into `10_knowledge/` only through an explicit extraction or review step. Active project context does not automatically become durable knowledge.

## Related

- Root agent rules: `AGENTS.md`
- Epistemic rules: `EPISTEMIC_STANCE.md`
- Architecture overview: `docs/architecture.md`
