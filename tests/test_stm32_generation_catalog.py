import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "docs/specs/stm32_generation_catalog_v0_1.json"


def _load_catalog():
    return json.loads(CATALOG_PATH.read_text())


def test_catalog_targets_cover_current_stm32_board_set():
    catalog = _load_catalog()
    catalog_board_ids = {entry["board_id"] for entry in catalog["targets"]}
    current_board_ids = {path.stem for path in (REPO_ROOT / "configs/boards").glob("stm32*.yaml")}
    assert catalog_board_ids == current_board_ids


def test_catalog_uses_valid_enums_and_required_fields():
    catalog = _load_catalog()
    enums = catalog["enums"]

    required_keys = {
        "board_id",
        "target_id",
        "display_name",
        "family",
        "generation_class",
        "validation_status",
        "baseline_recommendation",
        "notes",
        "pilot_assessment",
    }

    for entry in catalog["targets"]:
        assert required_keys.issubset(entry.keys())
        assert entry["family"] in enums["family"]
        assert entry["generation_class"] in enums["generation_class"]
        assert entry["validation_status"] in enums["validation_status"]
        assert entry["baseline_recommendation"] in enums["baseline_recommendation"]
        for category in ("process_hardening", "cross_family_proof"):
            assessment = entry["pilot_assessment"][category]
            assert assessment["recommendation"] in enums["pilot_recommendation_level"]
            assert assessment["reason"]


def test_official_source_targets_have_provenance_with_upstream_repo_and_revision():
    catalog = _load_catalog()
    official_targets = [entry for entry in catalog["targets"] if entry["generation_class"] == "official_source_based"]
    assert official_targets

    for entry in official_targets:
        provenance_path = REPO_ROOT / entry["official_source"]["provenance_path"]
        text = provenance_path.read_text()
        assert "repo:" in text
        assert "revision:" in text
        assert re.search(r"https://github\.com/STMicroelectronics/STM32Cube", text)


def test_catalog_recommendation_points_to_existing_targets():
    catalog = _load_catalog()
    board_ids = {entry["board_id"] for entry in catalog["targets"]}
    recommendation = catalog["second_pilot_recommendation"]
    assert recommendation["process_hardening_candidate"]["board_id"] in board_ids
    assert recommendation["cross_family_proof_candidate"]["board_id"] in board_ids
