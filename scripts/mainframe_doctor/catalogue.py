"""Load and validate doctor catalogue against required-invariants manifest."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_CHECK_FIELDS = (
    "id",
    "owner",
    "subsystem",
    "layer",
    "provider",
    "required",
    "mutates",
    "isolation",
    "timeout_seconds",
    "skip_policy",
    "pass_condition",
    "remediation",
    "safe_fix_available",
    "contract_version",
)


@dataclass
class CatalogueLoad:
    catalogue: dict[str, Any]
    required_ids: list[str]
    checks_by_id: dict[str, dict[str, Any]]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_catalogue(
    catalogue: dict[str, Any],
    required_ids: list[str],
) -> list[str]:
    errors: list[str] = []
    checks = catalogue.get("checks")
    if not isinstance(checks, list) or not checks:
        return ["catalogue.checks must be a non-empty list"]

    seen: set[str] = set()
    for i, check in enumerate(checks):
        if not isinstance(check, dict):
            errors.append(f"checks[{i}] is not an object")
            continue
        for field in REQUIRED_CHECK_FIELDS:
            if field not in check:
                errors.append(f"checks[{i}] missing field {field}")
        cid = check.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append(f"checks[{i}] missing id")
            continue
        if cid in seen:
            errors.append(f"duplicate check id: {cid}")
        seen.add(cid)
        if check.get("mutates") is True:
            errors.append(f"{cid}: mutates=true not allowed in doctor catalogue")
        provider = check.get("provider")
        if not provider:
            errors.append(f"{cid}: provider required")
        # Reporter-as-check guard: providers named *report* without threshold forbidden
        if isinstance(provider, str) and provider.endswith("_report") and not check.get("threshold"):
            errors.append(f"{cid}: reporter provider requires threshold adapter")

    # Completeness: every required invariant id must appear in catalogue
    missing = [rid for rid in required_ids if rid not in seen]
    for rid in missing:
        errors.append(f"catalogue missing required invariant id: {rid}")

    # Extra catalogue ids are allowed (forward-looking), but warn-as-error for empty owner
    for cid, check in ((c.get("id"), c) for c in checks if isinstance(c, dict)):
        if cid and not check.get("owner"):
            errors.append(f"{cid}: owner required")

    return errors


def load_catalogue_pair(
    catalogue_path: Path,
    invariants_path: Path,
) -> CatalogueLoad:
    errors: list[str] = []
    try:
        catalogue = load_json(catalogue_path)
    except Exception as exc:  # noqa: BLE001 — surface as config failure
        return CatalogueLoad({}, [], {}, [f"catalogue load failed: {exc}"])
    try:
        inv = load_json(invariants_path)
    except Exception as exc:  # noqa: BLE001
        return CatalogueLoad(catalogue, [], {}, [f"required-invariants load failed: {exc}"])

    required_ids = inv.get("required_check_ids")
    if not isinstance(required_ids, list) or not all(isinstance(x, str) for x in required_ids):
        errors.append("required-invariants.required_check_ids must be a string list")
        required_ids = []

    errors.extend(validate_catalogue(catalogue, required_ids))
    checks_by_id = {
        c["id"]: c
        for c in catalogue.get("checks", [])
        if isinstance(c, dict) and isinstance(c.get("id"), str)
    }
    return CatalogueLoad(catalogue, list(required_ids), checks_by_id, errors)
