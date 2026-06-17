from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from etymonoetic_interlingua.validator import CapsuleValidationError, load_capsule, validate_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ei",
        description="Validate and inspect etymonoetic semantic capsules.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate one or more capsule files.")
    validate_parser.add_argument("paths", nargs="+", type=Path)
    validate_parser.set_defaults(func=run_validate)

    show_parser = subparsers.add_parser("show", help="Print a compact capsule summary.")
    show_parser.add_argument("path", type=Path)
    show_parser.set_defaults(func=run_show)

    schema_parser = subparsers.add_parser("schema", help="Print the bundled capsule JSON Schema.")
    schema_parser.set_defaults(func=run_schema)

    return parser


def run_validate(args: argparse.Namespace) -> int:
    ok = True
    for path in args.paths:
        try:
            validate_file(path)
            print(f"OK {path}")
        except (CapsuleValidationError, OSError, json.JSONDecodeError) as exc:
            ok = False
            print(f"FAIL {path}", file=sys.stderr)
            print(exc, file=sys.stderr)
    return 0 if ok else 1


def run_show(args: argparse.Namespace) -> int:
    try:
        capsule = validate_file(args.path)
    except (CapsuleValidationError, OSError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 1

    surface = capsule["surface"]
    print(f"{surface['form']} ({surface['language']})")
    print(capsule["capsule_summary"])
    print()
    print("Present senses:")
    for sense in capsule["present_usage"]["senses"]:
        print(f"- {sense['id']}: {sense['definition']}")
    return 0


def run_schema(_args: argparse.Namespace) -> int:
    from etymonoetic_interlingua.validator import load_schema

    print(json.dumps(load_schema(), indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
