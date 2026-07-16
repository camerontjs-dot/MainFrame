"""CLI entry: python -m mainframe_doctor"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    # Ensure scripts/ is on path when executed as module from bin wrapper
    scripts_dir = Path(__file__).resolve().parents[1]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from mainframe_doctor.runner import format_human, run_doctor

    parser = argparse.ArgumentParser(
        prog="mainframe-doctor",
        description="Read-only MainFrame health aggregator (vector, not one boolean).",
    )
    profile = parser.add_mutually_exclusive_group()
    profile.add_argument("--quick", action="store_true", help="Session-start orientation profile (default)")
    profile.add_argument("--deep", action="store_true", help="Full catalogue profile")
    parser.add_argument("--component", metavar="SUBSYSTEM", help="Run one subsystem only")
    parser.add_argument("--json", action="store_true", help="JSON only on stdout")
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Fixture JSON file or directory (fixture.json); no live mutation",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="MainFrame root (default: detect from this install)",
    )
    parser.add_argument(
        "--catalogue",
        type=Path,
        default=None,
        help="Override catalogue path",
    )
    parser.add_argument(
        "--invariants",
        type=Path,
        default=None,
        help="Override required-invariants path",
    )
    args = parser.parse_args(argv)

    if args.root is not None:
        root = args.root.resolve()
    else:
        # bin/mainframe-doctor → repo root; or scripts/mainframe_doctor → parents[2]
        here = Path(__file__).resolve()
        root = here.parents[2]

    profile_name = "deep" if args.deep else "quick"
    report, code = run_doctor(
        root=root,
        profile=profile_name,
        component=args.component,
        fixture_path=args.fixture.resolve() if args.fixture else None,
        catalogue_path=args.catalogue.resolve() if args.catalogue else None,
        invariants_path=args.invariants.resolve() if args.invariants else None,
    )

    if args.json:
        # JSON only on stdout
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, sort_keys=False) + "\n")
    else:
        sys.stdout.write(format_human(report))

    return code


if __name__ == "__main__":
    raise SystemExit(main())
