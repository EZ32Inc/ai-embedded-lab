from __future__ import annotations

import json
from pathlib import Path

from ael.test_plan_schema import extract_plan_metadata


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_all_declared_schema_versions_validate_cleanly():
    plans_dir = REPO_ROOT / "tests" / "plans"
    structured_plan_paths = []

    for path in sorted(plans_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "schema_version" not in payload:
            continue
        structured_plan_paths.append(path.name)
        metadata = extract_plan_metadata(payload)
        assert metadata["validation_errors"] == [], f"{path.name}: {metadata['validation_errors']}"

    assert structured_plan_paths


def test_all_structured_baremetal_mailbox_plans_include_expected_metadata():
    plans_dir = REPO_ROOT / "tests" / "plans"
    checked = []

    for path in sorted(plans_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "1.0":
            continue
        if payload.get("test_kind") != "baremetal_mailbox":
            continue
        checked.append(path.name)
        assert isinstance(payload.get("supported_instruments"), list) and payload["supported_instruments"], path.name
        assert isinstance(payload.get("requires"), dict) and payload["requires"], path.name
        assert isinstance(payload.get("labels"), list) and payload["labels"], path.name
        assert isinstance(payload.get("covers"), list) and payload["covers"], path.name

    assert checked


def test_all_structured_instrument_specific_plans_include_expected_metadata():
    plans_dir = REPO_ROOT / "tests" / "plans"
    checked = []

    for path in sorted(plans_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "1.0":
            continue
        if payload.get("test_kind") != "instrument_specific":
            continue
        checked.append(path.name)
        assert isinstance(payload.get("supported_instruments"), list) and payload["supported_instruments"], path.name
        assert isinstance(payload.get("requires"), dict) and payload["requires"], path.name
        assert isinstance(payload.get("labels"), list) and payload["labels"], path.name
        assert isinstance(payload.get("covers"), list) and payload["covers"], path.name

    assert checked
