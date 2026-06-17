from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class CapsuleValidationError(ValueError):
    """Raised when a semantic capsule does not match the EI schema."""


def load_schema() -> dict[str, Any]:
    schema_path = resources.files("etymonoetic_interlingua.schemas").joinpath(
        "semantic-capsule.schema.json"
    )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def load_capsule(path: str | Path) -> dict[str, Any]:
    capsule_path = Path(path)
    return json.loads(capsule_path.read_text(encoding="utf-8"))


def validate_capsule(capsule: dict[str, Any]) -> dict[str, Any]:
    schema = load_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(capsule), key=lambda error: list(error.path))

    if errors:
        raise CapsuleValidationError(format_validation_errors(errors))

    provenance_errors = validate_provenance_refs(capsule)
    if provenance_errors:
        raise CapsuleValidationError("\n".join(provenance_errors))

    return capsule


def validate_file(path: str | Path) -> dict[str, Any]:
    return validate_capsule(load_capsule(path))


def format_validation_errors(errors: list[Any]) -> str:
    lines: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.path) or "<root>"
        lines.append(f"{location}: {error.message}")
    return "\n".join(lines)


def validate_provenance_refs(capsule: dict[str, Any]) -> list[str]:
    provenance_ids: list[str] = [
        entry["id"] for entry in capsule.get("provenance", []) if isinstance(entry, dict) and "id" in entry
    ]
    known_ids = set(provenance_ids)
    errors: list[str] = []

    duplicates = sorted({provenance_id for provenance_id in provenance_ids if provenance_ids.count(provenance_id) > 1})
    for duplicate in duplicates:
        errors.append(f"provenance: duplicate id {duplicate!r}")

    for path, refs in iter_provenance_refs(capsule):
        for ref in refs:
            if ref not in known_ids:
                errors.append(f"{format_path(path)}: unknown provenance ref {ref!r}")

    return errors


def iter_provenance_refs(value: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], list[str]]]:
    refs: list[tuple[tuple[str, ...], list[str]]] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = path + (key,)
            if key == "provenance_refs" and isinstance(nested, list):
                refs.append((nested_path, nested))
            else:
                refs.extend(iter_provenance_refs(nested, nested_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            refs.extend(iter_provenance_refs(nested, path + (str(index),)))
    return refs


def format_path(path: tuple[str, ...]) -> str:
    return ".".join(path) or "<root>"
