from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from etymonoetic_interlingua.cli import main
from etymonoetic_interlingua.sources import wiktionary_source
from etymonoetic_interlingua.templates import make_capsule_template
from etymonoetic_interlingua.training import training_records
from etymonoetic_interlingua.validator import (
    CapsuleValidationError,
    load_capsule,
    load_schema,
    validate_capsule,
    validate_file,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "examples"
CAPSULES = REPO_ROOT / "capsules"


def test_schema_loads() -> None:
    schema = load_schema()

    assert schema["title"] == "Etymonoetic Semantic Capsule"
    assert schema["properties"]["schema_version"]["const"] == "0.1.0"


def test_seed_examples_validate() -> None:
    for path in sorted(EXAMPLES.glob("*.json")):
        capsule = validate_file(path)
        assert capsule["schema_version"] == "0.1.0"


def test_curated_capsules_validate() -> None:
    paths = sorted((CAPSULES / "en").glob("*.json"))

    assert len(paths) >= 10
    for path in paths:
        capsule = validate_file(path)
        assert capsule["id"].startswith("ei:en:")
        assert any(source["source_type"] == "dictionary" for source in capsule["provenance"])


def test_capsule_manifest_paths_match_ids() -> None:
    manifest = json.loads((CAPSULES / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["set_id"] == "ei:capsules:en:cited-v0"
    for item in manifest["capsules"]:
        path = REPO_ROOT / item["path"]
        capsule = validate_file(path)
        assert path.exists()
        assert capsule["id"] == item["id"]
        assert capsule["surface"]["form"] == item["surface_form"]


def test_template_generates_valid_capsule() -> None:
    capsule = make_capsule_template("Sincere", language="en", part_of_speech="adjective")
    validated = validate_capsule(capsule)

    assert validated["id"] == "ei:en:sincere"
    assert validated["surface"]["normalized_form"] == "sincere"
    assert validated["uncertainty"]["overall"] == "unknown"


def test_wiktionary_source_can_seed_template() -> None:
    source = wiktionary_source("sincere", accessed="2026-06-17").to_provenance()
    capsule = make_capsule_template("sincere", part_of_speech="adjective", provenance=source)
    validated = validate_capsule(capsule)

    assert validated["provenance"][0]["id"] == "wiktionary-en-sincere"
    assert validated["provenance"][0]["url"] == "https://en.wiktionary.org/wiki/sincere"


def test_template_source_id_overrides_provenance_id_consistently() -> None:
    source = wiktionary_source("sincere", accessed="2026-06-17").to_provenance()
    capsule = make_capsule_template("sincere", source_id="custom-source", provenance=source)
    validated = validate_capsule(capsule)

    assert validated["provenance"][0]["id"] == "custom-source"
    assert validated["morphology"]["provenance_refs"] == ["custom-source"]


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


def test_cli_new_writes_valid_starter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "sincere.json"
    status = main(["new", "sincere", "--part-of-speech", "adjective", "--output", str(output)])

    captured = capsys.readouterr()
    assert status == 0
    assert f"WROTE {output}" in captured.out
    assert validate_file(output)["surface"]["form"] == "sincere"


def test_cli_new_can_seed_wiktionary_source(tmp_path: Path) -> None:
    output = tmp_path / "sincere.json"
    status = main(
        [
            "new",
            "sincere",
            "--part-of-speech",
            "adjective",
            "--wiktionary-source",
            "--output",
            str(output),
        ]
    )

    assert status == 0
    capsule = validate_file(output)
    assert capsule["provenance"][0]["source_type"] == "dictionary"
    assert capsule["provenance"][0]["url"] == "https://en.wiktionary.org/wiki/sincere"


def test_cli_expand_with_trace(capsys: pytest.CaptureFixture[str]) -> None:
    status = main(["expand", str(EXAMPLES / "radical.json"), "--trace"])

    captured = capsys.readouterr()
    assert status == 0
    assert "Radical should not be reduced to extreme." in captured.out
    assert "Trace:" in captured.out


def test_training_records_emit_two_tasks_per_capsule() -> None:
    capsule = validate_file(EXAMPLES / "iconoclast.json")
    records = training_records([capsule])

    assert [record["task"] for record in records] == [
        "text_to_capsule",
        "capsule_to_expansion",
    ]
    assert records[0]["output"]["id"] == "ei:en:iconoclast"


def test_cli_export_training_jsonl(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "training.jsonl"
    status = main(["export-training", str(EXAMPLES / "iconoclast.json"), "--output", str(output)])

    captured = capsys.readouterr()
    assert status == 0
    assert f"WROTE {output}" in captured.out

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["task"] == "text_to_capsule"
    assert json.loads(lines[1])["task"] == "capsule_to_expansion"
