# Scheduled Evaluation Workflow

Use this workflow to run MainFrame eval suites on a fixed cadence and feed
`20_live/eval-registry/` with trend data.

Binding: [process-evaluation.md](process-evaluation.md), [eval-methodology.md](eval-methodology.md), lane EV01.

## Cadence

| Cadence | When (launchd default) | Suite |
| --- | --- | --- |
| `daily` | 06:15 every day | ingest dry-run, mindgraph dry-run, project index check, eval-registry status |
| `weekly` | 07:30 Sundays | daily suite + unittest + **4-query fused MindGraph regression probe** + single eval-registry harvest |
| `monthly` | manual | weekly suite + `workflow-report --days 7 --json` |

Weekly/monthly runs also write an observational report to
`30_projects/mainframe-process-eval/outputs/YYYY-MM-DD-scheduled-<cadence>.md`
and re-harvest the registry.

## Commands

```bash
# Health (exit 1 if stale/missing launchd/failed weekly)
bin/eval-schedule check

# Run once (operator or CI)
bin/eval-schedule run --cadence weekly
bin/eval-schedule run --cadence weekly --full-probe   # 12 queries, fused+expanded (~2 min)
bin/eval-schedule run --cadence daily --dry-run

# Install macOS launchd agents (daily + weekly)
bin/eval-schedule install --cadence both
bin/eval-schedule status
bin/eval-schedule uninstall --cadence both
```

Operator card (read when check fails): `20_live/eval-registry/OPERATOR.md`

Logs: `20_live/eval-registry/logs/{daily,weekly}.{log,err}`
Manifest: `20_live/eval-registry/schedule-runs.jsonl`

## Visibility hooks (do not skip)

| When | Surface |
| --- | --- |
| Session start | `bin/session-open` prints eval-schedule health |
| Session end | `bin/session-close --check` warns if `bin/eval-schedule check` fails; the SessionEnd hook lands the same result in the tracker feed (ADR-040) |
| Compaction | `bin/session-close --checkpoint` (PreCompact hook) snapshots weekly-eval staleness into the draft + tracker feed |
| Handoff draft | `20_live/last-handoff-draft.md` includes eval-schedule status |
| Architecture | ADR-036 in `DECISIONS.md` |
| Research lane | EV01 `lanes/scheduled-process-evaluation/` |

## Weekly review (human, ~15 min)

1. `bin/eval-schedule status` — last run green?
2. `bin/eval-registry status` — new metrics/irregularities?
3. Read the latest `scheduled-weekly` output in `mainframe-process-eval/outputs/`.
4. Pick **one** improvement slice; rerun the same cadence after the fix.

## Guardrails

- Scheduled runs are **regression signal**, not promotion by themselves.
- MindGraph probe is skipped when `~/.mindgraph/mainframe.sqlite` is missing.
- Default weekly probe runs four fused regression queries (`q04_memory…`, `q07_ai_detection`, `q11/q12` scope negatives, ~25s). Use `--full-probe` for the complete matrix.
- `evaluation-feedback.md` files are excluded from harvest (not eval runs).
- Do not schedule behavioral `skill-eval` cases until receipt automation exists (EV02).
- Failed steps exit non-zero so launchd logs surface breakage.