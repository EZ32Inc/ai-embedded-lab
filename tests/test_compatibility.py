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
