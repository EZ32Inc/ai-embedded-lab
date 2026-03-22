"""Tests for ael.compatibility — Phase 1: Test ↔ Instrument resolution."""

import pytest

from ael.compatibility.model import CompatibilityResult, ExecutionPlan, Requirement
from ael.compatibility.registry import (
    provided_capabilities_from_surfaces,
    SURFACE_KEY_TO_CAPABILITIES,
    CAPABILITY_TO_SURFACE_KEYS,
    CANONICAL_CAPABILITY_TYPES,
)
from ael.compatibility.resolver import (
    resolve_test_instrument,
    resolve_execution_plan,
)
from ael.compatibility.explain import explain_compatibility, explain_plan


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_all_surface_keys_map_to_known_types(self):
        for sk, caps in SURFACE_KEY_TO_CAPABILITIES.items():
            for cap in caps:
                assert cap in CANONICAL_CAPABILITY_TYPES, (
                    f"surface key {sk!r} maps to unknown type {cap!r}"
                )

    def test_reverse_map_covers_all_surface_keys(self):
        all_sk_in_reverse: set = set()
        for keys in CAPABILITY_TO_SURFACE_KEYS.values():
            all_sk_in_reverse |= keys
        assert all_sk_in_reverse == set(SURFACE_KEY_TO_CAPABILITIES.keys())

    def test_provided_capabilities_empty(self):
        assert provided_capabilities_from_surfaces({}) == frozenset()

    def test_provided_capabilities_none(self):
        assert provided_capabilities_from_surfaces(None) == frozenset()  # type: ignore[arg-type]

    def test_provided_capabilities_swd_gives_flash_debug_reset(self):
        result = provided_capabilities_from_surfaces({"swd": "gdb_remote"})
        assert "flash_program" in result
        assert "debug_attach" in result
        assert "reset_control" in result

    def test_provided_capabilities_gpio_in_gives_logic_capture(self):
        result = provided_capabilities_from_surfaces({"gpio_in": "web_api"})
        assert "logic_capture" in result
        assert "gpio_input" in result

    def test_provided_capabilities_adc_gives_voltage(self):
        result = provided_capabilities_from_surfaces({"adc_in": "web_api"})
        assert "voltage_measure" in result
        assert "analog_in" in result

    def test_provided_capabilities_esp32jtag_full(self):
        # Real ESP32JTAG instrument instance surfaces
        surfaces = {
            "swd": "gdb_remote",
            "gpio_in": "web_api",
            "gpio_out": "web_api",
            "adc_in": "web_api",
            "reset_out": "web_api",
        }
        result = provided_capabilities_from_surfaces(surfaces)
        assert "flash_program" in result
        assert "debug_attach" in result
        assert "logic_capture" in result
        assert "voltage_measure" in result
        assert "gpio_output" in result
        assert "reset_control" in result

    def test_provided_capabilities_stlink(self):
        # Real ST-Link instance — only swd surface
        surfaces = {"swd": "gdb_remote"}
        result = provided_capabilities_from_surfaces(surfaces)
        assert "flash_program" in result
        assert "debug_attach" in result
        assert "reset_control" in result
        assert "logic_capture" not in result
        assert "voltage_measure" not in result

    def test_provided_capabilities_skips_empty_surface(self):
        surfaces = {"swd": "", "gpio_in": "web_api"}
        result = provided_capabilities_from_surfaces(surfaces)
        assert "flash_program" not in result  # swd surface was empty
        assert "logic_capture" in result      # gpio_in was present

    def test_provided_capabilities_unknown_key_ignored(self):
        surfaces = {"unknown_key": "some_surface", "swd": "gdb_remote"}
        result = provided_capabilities_from_surfaces(surfaces)
        assert "flash_program" in result
        # unknown_key contributes nothing — only known surface keys count
        assert len(result) == len(SURFACE_KEY_TO_CAPABILITIES["swd"])

    def test_esp32_meter_surfaces(self):
        # ESP32 meter: gpio_in, adc_in, gpio_out
        surfaces = {"gpio_in": "meter_tcp", "adc_in": "meter_tcp", "gpio_out": "meter_tcp"}
        result = provided_capabilities_from_surfaces(surfaces)
        assert "logic_capture" in result
        assert "voltage_measure" in result
        assert "gpio_output" in result
        assert "flash_program" not in result


# ---------------------------------------------------------------------------
# resolver — resolve_test_instrument
# ---------------------------------------------------------------------------

class TestResolveTestInstrument:
    def _esp32jtag_surfaces(self):
        return {
            "swd": "gdb_remote",
            "gpio_in": "web_api",
            "gpio_out": "web_api",
            "adc_in": "web_api",
            "reset_out": "web_api",
        }

    def _stlink_surfaces(self):
        return {"swd": "gdb_remote"}

    def _esp32_meter_surfaces(self):
        return {"gpio_in": "meter_tcp", "adc_in": "meter_tcp", "gpio_out": "meter_tcp"}

    def test_esp32jtag_gpio_signature_compatible(self):
        # GPIO signature test: needs flash + logic capture + reset
        result = resolve_test_instrument(
            ["flash_program", "logic_capture", "reset_control"],
            self._esp32jtag_surfaces(),
        )
        assert result.compatible is True
        assert result.score == 100

    def test_stlink_mailbox_test_compatible(self):
        # Mailbox test: needs flash + debug_attach (SWD memory read) + reset
        result = resolve_test_instrument(
            ["flash_program", "debug_attach", "reset_control"],
            self._stlink_surfaces(),
        )
        assert result.compatible is True
        assert result.score == 100

    def test_stlink_cannot_run_logic_capture_test(self):
        # ST-Link has no gpio_in — cannot run logic capture tests
        result = resolve_test_instrument(
            ["flash_program", "logic_capture"],
            self._stlink_surfaces(),
        )
        assert result.compatible is False
        assert "logic_capture" in result.missing_capabilities

    def test_meter_cannot_flash(self):
        # ESP32 meter has no SWD — cannot program firmware
        result = resolve_test_instrument(
            ["flash_program", "voltage_measure"],
            self._esp32_meter_surfaces(),
        )
        assert result.compatible is False
        assert "flash_program" in result.missing_capabilities

    def test_meter_compatible_voltage_only(self):
        result = resolve_test_instrument(
            ["voltage_measure", "logic_capture"],
            self._esp32_meter_surfaces(),
        )
        assert result.compatible is True

    def test_optional_capability_missing_does_not_fail(self):
        result = resolve_test_instrument(
            [
                {"type": "flash_program", "optional": False},
                {"type": "voltage_measure", "optional": True},
            ],
            self._stlink_surfaces(),  # no adc_in
        )
        assert result.compatible is True
        assert "voltage_measure" not in result.missing_capabilities
        assert any("voltage_measure" in w for w in result.warnings)

    def test_empty_requirements_always_compatible(self):
        result = resolve_test_instrument([], self._stlink_surfaces())
        assert result.compatible is True
        assert result.score == 100

    def test_empty_surfaces_fails_requirements(self):
        result = resolve_test_instrument(["flash_program"], {})
        assert result.compatible is False
        assert "flash_program" in result.missing_capabilities

    def test_score_partial_one_of_two(self):
        # flash_program present (via swd), logic_capture not → score = 50
        result = resolve_test_instrument(
            ["flash_program", "logic_capture"],
            self._stlink_surfaces(),
        )
        assert result.score == 50


# ---------------------------------------------------------------------------
# resolver — resolve_execution_plan
# ---------------------------------------------------------------------------

class TestResolveExecutionPlan:
    def _instruments(self):
        return {
            "esp32jtag": {
                "swd": "gdb_remote",
                "gpio_in": "web_api",
                "reset_out": "web_api",
            },
            "stlink": {
                "swd": "gdb_remote",
            },
        }

    def test_selects_instrument_that_satisfies_all(self):
        plan = resolve_execution_plan(
            ["flash_program", "logic_capture", "reset_control"],
            self._instruments(),
        )
        assert plan.executable is True
        assert "esp32jtag" in plan.selected_instruments

    def test_stlink_selected_when_only_flash_needed(self):
        plan = resolve_execution_plan(
            ["flash_program", "debug_attach"],
            {"stlink": {"swd": "gdb_remote"}},
        )
        assert plan.executable is True
        assert "stlink" in plan.selected_instruments

    def test_no_instruments_not_executable(self):
        plan = resolve_execution_plan(["flash_program"], {})
        assert plan.executable is False
        assert "flash_program" in plan.missing_requirements

    def test_no_instrument_satisfies_returns_best_partial(self):
        plan = resolve_execution_plan(
            ["voltage_measure", "flash_program"],
            {
                "meter": {"adc_in": "meter_tcp"},   # voltage but no flash
                "stlink": {"swd": "gdb_remote"},     # flash but no voltage
            },
        )
        assert plan.executable is False
        assert plan.missing_requirements

    def test_all_optional_no_match_still_executable(self):
        plan = resolve_execution_plan(
            [{"type": "voltage_measure", "optional": True}],
            {"stlink": {"swd": "gdb_remote"}},
        )
        assert plan.executable is True


# ---------------------------------------------------------------------------
# explain
# ---------------------------------------------------------------------------

class TestExplain:
    def test_explain_compatible(self):
        result = CompatibilityResult(
            compatible=True, score=100,
            reasons=["all 3 required capabilities satisfied"],
        )
        text = explain_compatibility(result)
        assert "COMPATIBLE" in text
        assert "100" in text

    def test_explain_not_compatible(self):
        result = CompatibilityResult(
            compatible=False, score=50,
            missing_capabilities=["logic_capture"],
            reasons=["1 required capability not satisfied"],
        )
        text = explain_compatibility(result)
        assert "NOT COMPATIBLE" in text
        assert "logic_capture" in text

    def test_explain_plan_executable(self):
        plan = ExecutionPlan(
            executable=True,
            selected_instruments=["esp32jtag"],
            reasons=["selected instrument 'esp32jtag' (score=100)"],
        )
        text = explain_plan(plan)
        assert "EXECUTABLE" in text
        assert "esp32jtag" in text

    def test_explain_plan_not_executable(self):
        plan = ExecutionPlan(
            executable=False,
            missing_requirements=["logic_capture"],
            reasons=["no instrument satisfies logic_capture"],
        )
        text = explain_plan(plan)
        assert "NOT EXECUTABLE" in text
        assert "logic_capture" in text


# ---------------------------------------------------------------------------
# Phase 2: DUT ↔ Test applicability
# ---------------------------------------------------------------------------

from ael.compatibility.model import DUTSpec, DUTTestCompatibilityResult, TestApplicabilitySpec
from ael.compatibility.resolver import resolve_dut_test


class TestDUTSpec:
    def test_from_dut_config_object(self):
        class FakeDUT:
            kind = "board"
            features = ["programmable_via_swd", "has_gpio"]
            board_id = "test_board"

        spec = DUTSpec.from_dut_config(FakeDUT())
        assert spec.kind == "board"
        assert "programmable_via_swd" in spec.features
        assert spec.board_id == "test_board"

    def test_from_dict(self):
        spec = DUTSpec.from_dut_config({"kind": "bare_mcu", "features": ["has_gpio"]})
        assert spec.kind == "bare_mcu"
        assert "has_gpio" in spec.features

    def test_from_empty(self):
        spec = DUTSpec.from_dut_config({})
        assert spec.kind == "board"
        assert spec.features == frozenset()

    def test_from_none(self):
        spec = DUTSpec.from_dut_config(None)
        assert spec.kind == "board"


class TestTestApplicabilitySpec:
    def test_from_test_raw(self):
        raw = {
            "applies_to": ["board", "bare_mcu"],
            "requires_dut_features": ["programmable_via_swd", "has_gpio"],
            "excludes_tags": ["not_programmable"],
        }
        spec = TestApplicabilitySpec.from_test_raw(raw)
        assert "board" in spec.applies_to
        assert "bare_mcu" in spec.applies_to
        assert "programmable_via_swd" in spec.requires_dut_features
        assert "not_programmable" in spec.excludes_tags

    def test_empty_applies_to_means_all(self):
        spec = TestApplicabilitySpec.from_test_raw({})
        assert spec.applies_to == frozenset()


class TestResolveDUTTest:
    def _board_dut(self, features=None):
        return DUTSpec(kind="board", features=frozenset(features or ["programmable_via_swd", "has_gpio"]))

    def _gpio_sig_test(self):
        return {
            "applies_to": ["board", "bare_mcu"],
            "requires_dut_features": ["programmable_via_swd", "has_gpio"],
        }

    def test_applicable_board_with_all_features(self):
        result = resolve_dut_test(self._board_dut(), self._gpio_sig_test())
        assert result.applicable is True
        assert not result.missing_features

    def test_wrong_dut_kind(self):
        dut = DUTSpec(kind="fpga_target", features=frozenset(["programmable_via_swd", "has_gpio"]))
        result = resolve_dut_test(dut, self._gpio_sig_test())
        assert result.applicable is False
        assert "fpga_target" in result.reasons[0]

    def test_missing_required_feature(self):
        dut = DUTSpec(kind="board", features=frozenset(["has_gpio"]))  # no programmable_via_swd
        result = resolve_dut_test(dut, self._gpio_sig_test())
        assert result.applicable is False
        assert "programmable_via_swd" in result.missing_features

    def test_excluded_by_tag(self):
        dut = DUTSpec(kind="board", features=frozenset(["programmable_via_swd", "has_gpio", "not_programmable"]))
        test = {
            "applies_to": ["board"],
            "requires_dut_features": ["has_gpio"],
            "excludes_tags": ["not_programmable"],
        }
        result = resolve_dut_test(dut, test)
        assert result.applicable is False
        assert "not_programmable" in result.excluded_by

    def test_no_applies_to_matches_all_kinds(self):
        # If applies_to is absent, test applies to all DUT kinds
        dut = DUTSpec(kind="fpga_target", features=frozenset())
        result = resolve_dut_test(dut, {})  # no applies_to
        assert result.applicable is True

    def test_accepts_dutconfig_object(self):
        class FakeDUT:
            kind = "board"
            features = ["programmable_via_swd", "has_gpio"]
            board_id = "test"
        result = resolve_dut_test(FakeDUT(), self._gpio_sig_test())
        assert result.applicable is True

    def test_bare_mcu_kind_applicable(self):
        dut = DUTSpec(kind="bare_mcu", features=frozenset(["programmable_via_swd", "has_gpio"]))
        result = resolve_dut_test(dut, self._gpio_sig_test())
        assert result.applicable is True

    def test_esp32c6_meter_test(self):
        dut = DUTSpec(kind="board", features=frozenset(["programmable_via_jtag", "has_uart_console", "has_gpio", "has_adc"]))
        test = {
            "applies_to": ["board", "soc"],
            "requires_dut_features": ["has_gpio", "has_adc"],
        }
        result = resolve_dut_test(dut, test)
        assert result.applicable is True

    def test_dut_loader_integration(self):
        """DUTConfig loaded from board YAML has kind and features parsed."""
        from pathlib import Path
        from ael.dut.registry import load_dut_from_file
        repo_root = Path(__file__).resolve().parents[1]
        dut = load_dut_from_file(repo_root, "stm32f411ceu6")
        assert dut.kind == "board"
        assert "programmable_via_swd" in dut.features
        assert "has_gpio" in dut.features

    def test_dut_loader_stm32f103_stlink(self):
        from pathlib import Path
        from ael.dut.registry import load_dut_from_file
        repo_root = Path(__file__).resolve().parents[1]
        dut = load_dut_from_file(repo_root, "stm32f103_gpio_stlink")
        assert dut.kind == "bare_mcu"
        assert "programmable_via_swd" in dut.features

    def test_end_to_end_stm32f411_applicable(self):
        from pathlib import Path
        from ael.dut.registry import load_dut_from_file
        import json
        repo_root = Path(__file__).resolve().parents[1]
        dut = load_dut_from_file(repo_root, "stm32f411ceu6")
        with open(repo_root / "tests/plans/stm32f411_gpio_signature.json") as f:
            test_raw = json.load(f)
        result = resolve_dut_test(dut, test_raw)
        assert result.applicable is True


# ---------------------------------------------------------------------------
# Phase 3: DUT ↔ Instrument physical/protocol compatibility
# ---------------------------------------------------------------------------

from ael.compatibility.model import DUTInstrumentCompatibilityResult
from ael.compatibility.resolver import resolve_dut_instrument


class TestResolveDUTInstrument:
    def _swd_dut(self, extra_features=None):
        features = ["programmable_via_swd", "has_gpio", "has_reset_pin"]
        return DUTSpec(kind="board", features=frozenset(features + (extra_features or [])), board_id="test_board")

    def _esp32_dut(self):
        return DUTSpec(kind="board", features=frozenset(["programmable_via_jtag", "has_uart_console", "has_gpio", "has_adc"]), board_id="esp32c6")

    def _esp32jtag_surfaces(self):
        return {"swd": "gdb_remote", "gpio_in": "web_api", "gpio_out": "web_api", "adc_in": "web_api", "reset_out": "web_api"}

    def _stlink_surfaces(self):
        return {"swd": "gdb_remote"}

    def _meter_surfaces(self):
        return {"gpio_in": "meter_tcp", "adc_in": "meter_tcp", "gpio_out": "meter_tcp"}

    def test_esp32jtag_compatible_with_swd_dut(self):
        result = resolve_dut_instrument(self._swd_dut(), self._esp32jtag_surfaces())
        assert result.compatible is True
        assert not result.missing_surfaces

    def test_stlink_compatible_with_swd_dut(self):
        # ST-Link has swd surface — sufficient for SWD-programmable DUT
        result = resolve_dut_instrument(self._swd_dut(), self._stlink_surfaces())
        assert result.compatible is True
        assert not result.missing_surfaces

    def test_stlink_generates_warnings_for_missing_optionals(self):
        # ST-Link has no gpio_in/reset_out — optional surfaces → warnings, not failure
        dut = DUTSpec(kind="board", features=frozenset(["programmable_via_swd", "has_gpio", "has_reset_pin"]), board_id="test")
        result = resolve_dut_instrument(dut, self._stlink_surfaces())
        assert result.compatible is True
        assert result.warnings  # missing gpio_in and/or reset_out generate warnings

    def test_meter_incompatible_with_swd_dut(self):
        # ESP32 meter has no swd — cannot program SWD-programmable DUT
        result = resolve_dut_instrument(self._swd_dut(), self._meter_surfaces())
        assert result.compatible is False
        assert "swd" in result.missing_surfaces

    def test_esp32_dut_no_required_surfaces(self):
        # programmable_via_jtag uses esptool (no instrument surface required)
        # So meter is compatible at the DUT↔Instrument level
        result = resolve_dut_instrument(self._esp32_dut(), self._meter_surfaces())
        assert result.compatible is True

    def test_empty_surfaces_fails_swd_dut(self):
        result = resolve_dut_instrument(self._swd_dut(), {})
        assert result.compatible is False
        assert "swd" in result.missing_surfaces

    def test_dut_no_features_always_compatible(self):
        # A DUT with no known features has no required surfaces
        dut = DUTSpec(kind="board", features=frozenset())
        result = resolve_dut_instrument(dut, {})
        assert result.compatible is True

    def test_accepts_dutconfig_object(self):
        from pathlib import Path
        from ael.dut.registry import load_dut_from_file
        repo_root = Path(__file__).resolve().parents[1]
        dut = load_dut_from_file(repo_root, "stm32f411ceu6")
        surfaces = {"swd": "gdb_remote", "gpio_in": "web_api", "reset_out": "web_api"}
        result = resolve_dut_instrument(dut, surfaces)
        assert result.compatible is True

    def test_stm32f103_stlink_compatible(self):
        from pathlib import Path
        from ael.dut.registry import load_dut_from_file
        repo_root = Path(__file__).resolve().parents[1]
        dut = load_dut_from_file(repo_root, "stm32f103_gpio_stlink")
        result = resolve_dut_instrument(dut, {"swd": "gdb_remote"})
        assert result.compatible is True

    def test_esp32c6_meter_compatible_no_swd_needed(self):
        from pathlib import Path
        from ael.dut.registry import load_dut_from_file
        repo_root = Path(__file__).resolve().parents[1]
        dut = load_dut_from_file(repo_root, "esp32c6_devkit")
        # meter provides gpio_in, adc_in, gpio_out — no swd needed for esp32
        result = resolve_dut_instrument(dut, {"gpio_in": "meter_tcp", "adc_in": "meter_tcp"})
        assert result.compatible is True
