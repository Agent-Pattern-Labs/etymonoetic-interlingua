from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from etymonoetic_interlingua.cli import main
from etymonoetic_interlingua.validator import (
    CapsuleValidationError,
    load_capsule,
    load_schema,
    validate_capsule,
    validate_file,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "examples"


def test_schema_loads() -> None:
    schema = load_schema()

    assert schema["title"] == "Etymonoetic Semantic Capsule"
    assert schema["properties"]["schema_version"]["const"] == "0.1.0"


def test_seed_examples_validate() -> None:
    for path in sorted(EXAMPLES.glob("*.json")):
        capsule = validate_file(path)
        assert capsule["schema_version"] == "0.1.0"


def test_required_layers_are_enforced() -> None:
    capsule = load_capsule(EXAMPLES / "iconoclast.json")
    del capsule["pragmatics"]

    with pytest.raises(CapsuleValidationError) as excinfo:
        validate_capsule(capsule)

    assert "pragmatics" in str(excinfo.value)


def test_unknown_provenance_refs_are_rejected() -> None:
    capsule = load_capsule(EXAMPLES / "radical.json")
    broken = deepcopy(capsule)
    broken["morphology"]["segments"][0]["provenance_refs"] = ["missing-source"]

    with pytest.raises(CapsuleValidationError) as excinfo:
        validate_capsule(broken)

    assert "unknown provenance ref 'missing-source'" in str(excinfo.value)


def test_cli_validate_examples(capsys: pytest.CaptureFixture[str]) -> None:
    status = main(
        [
            "validate",
            str(EXAMPLES / "iconoclast.json"),
            str(EXAMPLES / "radical.json"),
        ]
    )

    captured = capsys.readouterr()
    assert status == 0
    assert "OK" in captured.out


def test_cli_show_summary(capsys: pytest.CaptureFixture[str]) -> None:
    status = main(["show", str(EXAMPLES / "iconoclast.json")])

    captured = capsys.readouterr()
    assert status == 0
    assert "iconoclast (en)" in captured.out
    assert "Present senses:" in captured.out
