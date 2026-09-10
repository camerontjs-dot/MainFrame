#!/usr/bin/env python3
"""Score loop catalogue entries and enforce tier thresholds.

Usage (from MainFrame root):
  python3 40_operations/mainframe-process-eval/workbench/loop-eval/scripts/score_catalogue.py
  python3 .../score_catalogue.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
CATALOGUE_JSON = (
    Path(__file__).resolve().parents[1] / "catalogue" / "entries.json"
)
CATALOGUE_YAML = (
    Path(__file__).resolve().parents[1] / "catalogue" / "entries.yaml"
)
CATALOGUE = CATALOGUE_JSON if CATALOGUE_JSON.exists() else CATALOGUE_YAML
CHECKLIST_KEYS = [
    "unit_of_work",
    "entry_exit",
    "close_or_loop_decision",
    "workflow_contract",
    "skill_or_agent_procedure",
    "bin_cli",
    "dogfood_evidence",
    "promotion_destinations",
    "anti_scope",
    "eval_or_action_surface",
]

# Tier A required checklist keys (in addition to score ≥ 8)
TIER_A_REQUIRED = (
    "unit_of_work",
    "entry_exit",
    "workflow_contract",
    "dogfood_evidence",
)


def load_catalogue(path: Path = CATALOGUE) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise SystemExit(
                "entries.json missing and PyYAML not installed; "
                "prefer catalogue/entries.json"
            ) from exc
        data = yaml.safe_load(text)
    if not isinstance(data, dict) or "entries" not in data:
        raise SystemExit(f"invalid catalogue: {path}")
    return data


def score_entry(entry: dict[str, Any]) -> int:
    cl = entry.get("checklist") or {}
    return sum(1 for k in CHECKLIST_KEYS if cl.get(k) is True)


def tier_a_gates_ok(entry: dict[str, Any]) -> bool:
    cl = entry.get("checklist") or {}
    if not all(cl.get(k) is True for k in TIER_A_REQUIRED):
        return False
    # bin OR skill
    if not (cl.get("bin_cli") or cl.get("skill_or_agent_procedure")):
        return False
    return score_entry(entry) >= 8


def expected_tier(entry: dict[str, Any]) -> str:
    """Suggest tier from score + gates (does not auto-rename candidates)."""
    declared = entry.get("tier")
    s = score_entry(entry)
    if declared == "candidate":
        return "candidate"
    if tier_a_gates_ok(entry):
        return "well_defined"
    if s >= 4:
        return "underspecified"
    return "underspecified"


def validate_entry(entry: dict[str, Any], root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    eid = entry.get("id", "?")
    cl = entry.get("checklist") or {}
    for k in CHECKLIST_KEYS:
        if k not in cl or not isinstance(cl[k], bool):
            problems.append(f"{eid}: checklist missing bool {k}")

    computed = score_entry(entry)
    if entry.get("score") is not None and int(entry["score"]) != computed:
        problems.append(
            f"{eid}: score field {entry.get('score')} != computed {computed}"
        )

    tier = entry.get("tier")
    if tier == "well_defined":
        if not tier_a_gates_ok(entry):
            problems.append(
                f"{eid}: tier well_defined but fails A gates/score "
                f"(score={computed})"
            )
    elif tier == "underspecified":
        if tier_a_gates_ok(entry):
            problems.append(
                f"{eid}: tier underspecified but meets A gates — reclassify?"
            )
        if computed < 4 and entry.get("status") != "draft":
            problems.append(
                f"{eid}: underspecified with score {computed} < 4 "
                "(raise evidence or mark candidate/draft)"
            )
    elif tier == "candidate":
        pass
    else:
        problems.append(f"{eid}: unknown tier {tier!r}")

    surfaces = entry.get("surfaces") or {}
    for key in ("workflow", "skill", "bin", "owner"):
        rel = surfaces.get(key)
        if not rel:
            continue
        # owner may be multi-token description
        if key == "owner" and (" " in rel or "+" in rel):
            continue
        path = root / rel
        if not path.exists():
            problems.append(f"{eid}: surface {key} path missing: {rel}")

    return problems


def validate_catalogue(data: dict[str, Any], root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    entries = data.get("entries") or []
    ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            problems.append("non-mapping entry")
            continue
        eid = str(entry.get("id", ""))
        if not eid:
            problems.append("entry missing id")
            continue
        if eid in ids:
            problems.append(f"duplicate id: {eid}")
        ids.append(eid)
        problems.extend(validate_entry(entry, root=root))

    # edge references should resolve when present
    idset = set(ids)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        edges = entry.get("edges") or {}
        for direction in ("feeds", "fed_by"):
            for ref in edges.get(direction) or []:
                if ref not in idset:
                    problems.append(
                        f"{entry.get('id')}: edge {direction} unknown id {ref}"
                    )
    return problems


def summary(data: dict[str, Any]) -> dict[str, Any]:
    entries = [e for e in data.get("entries") or [] if isinstance(e, dict)]
    by_tier: dict[str, list[str]] = {
        "well_defined": [],
        "underspecified": [],
        "candidate": [],
    }
    scored = []
    for e in entries:
        s = score_entry(e)
        scored.append({"id": e.get("id"), "tier": e.get("tier"), "score": s})
        t = e.get("tier") or "candidate"
        if t in by_tier:
            by_tier[t].append(f"{e.get('id')} ({s}/10)")
    return {
        "n": len(entries),
        "by_tier_counts": {k: len(v) for k, v in by_tier.items()},
        "by_tier": by_tier,
        "scores": scored,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--catalogue", type=Path, default=CATALOGUE)
    parser.add_argument(
        "--out",
        type=Path,
        help="optional path to write the JSON report (local-only; not a Git surface)",
    )
    args = parser.parse_args()

    data = load_catalogue(args.catalogue)
    # stamp computed scores into report only
    for e in data.get("entries") or []:
        if isinstance(e, dict):
            e["_computed_score"] = score_entry(e)

    problems = validate_catalogue(data, root=ROOT)
    summ = summary(data)
    report = {"summary": summ, "problems": problems, "ok": not problems}

    if args.json or args.out:
        payload = json.dumps(report, indent=2) + "\n"
        if args.json or not args.out:
            print(payload, end="")
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(payload, encoding="utf-8")
    else:
        try:
            shown = args.catalogue.resolve().relative_to(ROOT)
        except ValueError:
            shown = args.catalogue
        print(f"catalogue: {shown}")
        print(f"entries: {summ['n']}  tiers: {summ['by_tier_counts']}")
        for tier, rows in summ["by_tier"].items():
            print(f"\n[{tier}]")
            for row in rows:
                print(f"  - {row}")
        if problems:
            print(f"\nPROBLEMS ({len(problems)}):")
            for p in problems:
                print(f"  - {p}")
        else:
            print("\nOK — tier/score/surface checks passed")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
