import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "docs/specs/example_generation_catalog_v0_1.json"


def _load_catalog():
    return json.loads(CATALOG_PATH.read_text())


def test_example_catalog_entries_use_valid_enums_and_required_fields():
    catalog = _load_catalog()
    enums = catalog["enums"]
    required_keys = {
        "board_id",
        "family",
        "example_kind",
        "plan",
        "target",
        "source_basis",
        "validation_status",
        "contract_completeness",
        "build_status",
        "runtime_validation_status",
        "family_method",
    }

    for entry in catalog["examples"]:
        assert required_keys.issubset(entry.keys())
        assert entry["family"] in enums["family"]
        assert entry["example_kind"] in enums["example_kind"]
        assert entry["source_basis"] in enums["source_basis"]
        assert entry["validation_status"] in enums["validation_status"]
        assert entry["contract_completeness"] in enums["contract_completeness"]
        assert entry["build_status"] in enums["build_status"]
        assert entry["runtime_validation_status"] in enums["runtime_validation_status"]
        assert entry["family_method"] in enums["family_method"]


def test_example_catalog_paths_exist():
    catalog = _load_catalog()
    for entry in catalog["examples"]:
        assert (REPO_ROOT / entry["plan"]).exists()
        assert (REPO_ROOT / entry["target"]).exists()


def test_adc_examples_are_marked_as_unbound_external_input_contracts():
    catalog = _load_catalog()
    adc_entries = [entry for entry in catalog["examples"] if entry["example_kind"] == "adc_banner"]
    assert adc_entries
    for entry in adc_entries:
        assert entry["contract_completeness"] == "formal_contract_complete_with_unbound_external_inputs"


def test_non_adc_examples_are_marked_as_formal_contract_complete():
    catalog = _load_catalog()
    for entry in catalog["examples"]:
        if entry["example_kind"] != "adc_banner":
            assert entry["contract_completeness"] == "formal_contract_complete"
