"""
Tests for validate_dut_manifest() — new board-centric DUT spec validation.
"""

import pytest
from ael.assets import validate_dut_manifest


# ── Helpers ─────────────────────────────────────────────────────────────────

def _minimal_valid():
    """Minimal manifest that passes validate_dut_manifest()."""
    return {
        "id": "test_board",
        "name": "Test Board",
        "lifecycle_stage": "golden",
        "mcus": [
            {
                "id": "main",
                "mcu": "stm32f411ceu6",
                "family": "stm32f4",
                "role": "dut",
                "build": {"type": "arm_debug", "project_dir": "firmware"},
                "flash": {"method": "gdb_swd"},
            }
        ],
        "board_configs": [
            {
                "id": "esp32jtag",
                "path": "configs/boards/test_board.yaml",
                "instrument_family": "esp32jtag",
            }
        ],
    }


# ── Non-dict input ───────────────────────────────────────────────────────────

class TestNonDictInput:
    def test_none_returns_error(self):
        errors = validate_dut_manifest(None)
        assert errors == ["manifest must be a dict"]

    def test_string_returns_error(self):
        errors = validate_dut_manifest("not a dict")
        assert errors == ["manifest must be a dict"]

    def test_list_returns_error(self):
        errors = validate_dut_manifest([])
        assert errors == ["manifest must be a dict"]


# ── Minimal valid manifest ───────────────────────────────────────────────────

class TestMinimalValid:
    def test_minimal_valid_has_no_errors(self):
        assert validate_dut_manifest(_minimal_valid()) == []

    def test_empty_manifest_produces_errors(self):
        errors = validate_dut_manifest({})
        assert "name: required" in errors

    def test_missing_name_reported(self):
        m = _minimal_valid()
        del m["name"]
        errors = validate_dut_manifest(m)
        assert "name: required" in errors

    def test_empty_name_reported(self):
        m = _minimal_valid()
        m["name"] = ""
        errors = validate_dut_manifest(m)
        assert "name: required" in errors


# ── lifecycle_stage ──────────────────────────────────────────────────────────

class TestLifecycleStage:
    def test_valid_stages_pass(self):
        for stage in ("golden", "draft", "runnable", "validated"):
            m = _minimal_valid()
            m["lifecycle_stage"] = stage
            assert validate_dut_manifest(m) == [], f"stage {stage!r} should be valid"

    def test_invalid_stage_reported(self):
        m = _minimal_valid()
        m["lifecycle_stage"] = "production"
        errors = validate_dut_manifest(m)
        assert any("lifecycle_stage" in e and "production" in e for e in errors)

    def test_missing_lifecycle_stage_not_required(self):
        # lifecycle_stage is not required by validate_dut_manifest (only checked if present)
        m = _minimal_valid()
        del m["lifecycle_stage"]
        assert validate_dut_manifest(m) == []


# ── mcus[] ───────────────────────────────────────────────────────────────────

class TestMcus:
    def test_mcus_missing_is_ok(self):
        # mcus is only validated when present
        m = _minimal_valid()
        del m["mcus"]
        assert validate_dut_manifest(m) == []

    def test_mcus_empty_list_is_error(self):
        m = _minimal_valid()
        m["mcus"] = []
        errors = validate_dut_manifest(m)
        assert any("mcus" in e and "non-empty" in e for e in errors)

    def test_mcus_not_list_is_error(self):
        m = _minimal_valid()
        m["mcus"] = "not a list"
        errors = validate_dut_manifest(m)
        assert any("mcus" in e and "non-empty" in e for e in errors)

    def test_mcu_entry_not_dict_is_error(self):
        m = _minimal_valid()
        m["mcus"] = ["not a dict"]
        errors = validate_dut_manifest(m)
        assert any("mcus[0]: must be a dict" in e for e in errors)

    def test_missing_mcu_id_reported(self):
        m = _minimal_valid()
        del m["mcus"][0]["id"]
        errors = validate_dut_manifest(m)
        assert any("mcus[0].id: required" in e for e in errors)

    def test_missing_mcu_part_reported(self):
        m = _minimal_valid()
        del m["mcus"][0]["mcu"]
        errors = validate_dut_manifest(m)
        assert any("mcus[0].mcu: required" in e for e in errors)

    def test_missing_family_reported(self):
        m = _minimal_valid()
        del m["mcus"][0]["family"]
        errors = validate_dut_manifest(m)
        assert any("mcus[0].family: required" in e for e in errors)

    def test_missing_role_reported(self):
        m = _minimal_valid()
        del m["mcus"][0]["role"]
        errors = validate_dut_manifest(m)
        assert any("mcus[0].role: required" in e for e in errors)

    def test_invalid_role_reported(self):
        m = _minimal_valid()
        m["mcus"][0]["role"] = "master"
        errors = validate_dut_manifest(m)
        assert any("mcus[0].role" in e and "master" in e for e in errors)

    def test_valid_roles_pass(self):
        for role in ("dut", "debugger", "coprocessor"):
            m = _minimal_valid()
            m["mcus"][0]["role"] = role
            if role != "dut":
                # debugger/coprocessor don't need build/flash
                del m["mcus"][0]["build"]
                del m["mcus"][0]["flash"]
            assert validate_dut_manifest(m) == [], f"role {role!r} should be valid"

    def test_dut_role_requires_build(self):
        m = _minimal_valid()
        del m["mcus"][0]["build"]
        errors = validate_dut_manifest(m)
        assert any("mcus[0].build: required for role=dut" in e for e in errors)

    def test_dut_role_requires_flash(self):
        m = _minimal_valid()
        del m["mcus"][0]["flash"]
        errors = validate_dut_manifest(m)
        assert any("mcus[0].flash: required for role=dut" in e for e in errors)

    def test_debugger_role_does_not_require_build(self):
        m = _minimal_valid()
        m["mcus"].append({"id": "stlink", "mcu": "stm32f103cbt6", "family": "stm32f1", "role": "debugger"})
        assert validate_dut_manifest(m) == []

    def test_invalid_build_type_reported(self):
        m = _minimal_valid()
        m["mcus"][0]["build"]["type"] = "bazel"
        errors = validate_dut_manifest(m)
        assert any("mcus[0].build.type" in e and "bazel" in e for e in errors)

    def test_valid_build_types_pass(self):
        for bt in ("arm_debug", "idf", "cmake", "pico"):
            m = _minimal_valid()
            m["mcus"][0]["build"]["type"] = bt
            assert validate_dut_manifest(m) == [], f"build type {bt!r} should be valid"

    def test_invalid_flash_method_reported(self):
        m = _minimal_valid()
        m["mcus"][0]["flash"]["method"] = "openocd"
        errors = validate_dut_manifest(m)
        assert any("mcus[0].flash.method" in e and "openocd" in e for e in errors)

    def test_valid_flash_methods_pass(self):
        for fm in ("gdb_swd", "gdb_stutil", "idf_esptool"):
            m = _minimal_valid()
            m["mcus"][0]["flash"]["method"] = fm
            assert validate_dut_manifest(m) == [], f"flash method {fm!r} should be valid"

    def test_missing_build_project_dir_reported(self):
        m = _minimal_valid()
        del m["mcus"][0]["build"]["project_dir"]
        errors = validate_dut_manifest(m)
        assert any("mcus[0].build.project_dir: required" in e for e in errors)

    def test_multi_mcu_validates_all_entries(self):
        m = _minimal_valid()
        m["mcus"].append({"id": "bad", "mcu": "x", "family": "y", "role": "invalid_role"})
        errors = validate_dut_manifest(m)
        assert any("mcus[1].role" in e for e in errors)


# ── board_configs[] ──────────────────────────────────────────────────────────

class TestBoardConfigs:
    def test_board_configs_missing_is_ok(self):
        m = _minimal_valid()
        del m["board_configs"]
        assert validate_dut_manifest(m) == []

    def test_board_configs_empty_list_is_error(self):
        m = _minimal_valid()
        m["board_configs"] = []
        errors = validate_dut_manifest(m)
        assert any("board_configs" in e and "non-empty" in e for e in errors)

    def test_board_config_not_dict_is_error(self):
        m = _minimal_valid()
        m["board_configs"] = ["not a dict"]
        errors = validate_dut_manifest(m)
        assert any("board_configs[0]: must be a dict" in e for e in errors)

    def test_missing_config_id_reported(self):
        m = _minimal_valid()
        del m["board_configs"][0]["id"]
        errors = validate_dut_manifest(m)
        assert any("board_configs[0].id: required" in e for e in errors)

    def test_missing_config_path_reported(self):
        m = _minimal_valid()
        del m["board_configs"][0]["path"]
        errors = validate_dut_manifest(m)
        assert any("board_configs[0].path: required" in e for e in errors)

    def test_missing_instrument_family_reported(self):
        m = _minimal_valid()
        del m["board_configs"][0]["instrument_family"]
        errors = validate_dut_manifest(m)
        assert any("board_configs[0].instrument_family: required" in e for e in errors)

    def test_invalid_instrument_family_reported(self):
        m = _minimal_valid()
        m["board_configs"][0]["instrument_family"] = "usb_direct"
        errors = validate_dut_manifest(m)
        assert any("board_configs[0].instrument_family" in e and "usb_direct" in e for e in errors)

    def test_valid_instrument_families_pass(self):
        for fam in ("esp32jtag", "stlink", "esp32_meter", "none"):
            m = _minimal_valid()
            m["board_configs"][0]["instrument_family"] = fam
            assert validate_dut_manifest(m) == [], f"instrument_family {fam!r} should be valid"

    def test_multiple_board_configs_all_validated(self):
        m = _minimal_valid()
        m["board_configs"].append({"id": "stlink", "path": "x.yaml", "instrument_family": "bad"})
        errors = validate_dut_manifest(m)
        assert any("board_configs[1].instrument_family" in e for e in errors)


# ── Integration: all 12 golden DUT manifests pass ────────────────────────────

class TestGoldenManifests:
    def test_all_golden_manifests_pass_validation(self):
        from ael.assets import _load_yaml
        from pathlib import Path

        root = Path("assets_golden/duts")
        failures = {}
        for dut_dir in sorted(root.iterdir()):
            manifest_path = dut_dir / "manifest.yaml"
            if not manifest_path.exists():
                continue
            manifest = _load_yaml(manifest_path)
            errors = validate_dut_manifest(manifest)
            if errors:
                failures[dut_dir.name] = errors

        assert failures == {}, f"Golden manifests with validation errors:\n" + "\n".join(
            f"  {k}: {v}" for k, v in failures.items()
        )
