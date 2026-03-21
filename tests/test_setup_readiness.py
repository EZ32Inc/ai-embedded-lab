import unittest

from ael.connection_model import (
    SetupComponentStatus,
    build_setup_readiness,
)
from ael.connection_metadata import validate_power_and_boot


class TestBuildSetupReadiness(unittest.TestCase):
    def test_empty_bench_setup_is_not_applicable(self):
        result = build_setup_readiness({})
        self.assertEqual(result.overall, SetupComponentStatus.NOT_APPLICABLE)
        self.assertTrue(result.ready_to_run)
        self.assertEqual(result.blocking_issues, [])

    def test_non_dict_bench_setup_is_not_applicable(self):
        result = build_setup_readiness(None)
        self.assertEqual(result.overall, SetupComponentStatus.NOT_APPLICABLE)
        self.assertTrue(result.ready_to_run)

    def test_provisioned_instrument_role_ready(self):
        bench_setup = {
            "instrument_roles": [
                {"role": "power_supply", "instrument_id": "ps1", "status": "provisioned", "required": True},
            ]
        }
        result = build_setup_readiness(bench_setup)
        self.assertEqual(result.overall, SetupComponentStatus.PROVISIONED_UNVERIFIED)
        self.assertTrue(result.ready_to_run)
        self.assertEqual(len(result.components), 1)
        self.assertEqual(result.components[0].component_type, "instrument_role")
        self.assertEqual(result.components[0].component_id, "power_supply")

    def test_defined_not_provisioned_external_input_blocks(self):
        bench_setup = {
            "external_inputs": [
                {"dut_signal": "SIG_IN", "kind": "clock", "status": "defined_not_provisioned", "required": True},
            ]
        }
        result = build_setup_readiness(bench_setup)
        self.assertEqual(result.overall, SetupComponentStatus.DEFINED_NOT_PROVISIONED)
        self.assertFalse(result.ready_to_run)
        self.assertEqual(len(result.blocking_issues), 1)
        self.assertIn("defined_not_provisioned", result.blocking_issues[0])

    def test_manually_unspecified_blocks_and_takes_precedence(self):
        bench_setup = {
            "instrument_roles": [
                {"role": "scope", "instrument_id": "osc1", "status": "manual_loopback_required", "required": True},
                {"role": "dut_power", "instrument_id": "ps1", "status": "provisioned", "required": True},
            ]
        }
        result = build_setup_readiness(bench_setup)
        self.assertEqual(result.overall, SetupComponentStatus.MANUALLY_UNSPECIFIED)
        self.assertFalse(result.ready_to_run)

    def test_optional_blocking_status_does_not_block(self):
        bench_setup = {
            "external_inputs": [
                {"dut_signal": "OPT_CLK", "kind": "clock", "status": "defined_not_provisioned", "required": False},
            ]
        }
        result = build_setup_readiness(bench_setup)
        # optional component with blocking status should not block overall
        self.assertTrue(result.ready_to_run)
        self.assertEqual(result.blocking_issues, [])

    def test_dut_to_instrument_is_provisioned_unverified(self):
        bench_setup = {
            "dut_to_instrument": [
                {"dut_gpio": "PA4", "inst_gpio": "0"},
            ]
        }
        result = build_setup_readiness(bench_setup)
        self.assertEqual(result.overall, SetupComponentStatus.PROVISIONED_UNVERIFIED)
        self.assertTrue(result.ready_to_run)
        self.assertEqual(result.components[0].component_type, "dut_to_instrument")

    def test_verified_status_maps_correctly(self):
        bench_setup = {
            "instrument_roles": [
                {"role": "jtag", "instrument_id": "probe1", "status": "verified", "required": True},
            ]
        }
        result = build_setup_readiness(bench_setup)
        self.assertEqual(result.overall, SetupComponentStatus.VERIFIED)
        self.assertTrue(result.ready_to_run)

    def test_to_dict_serializes_correctly(self):
        bench_setup = {
            "instrument_roles": [
                {"role": "power", "instrument_id": "ps1", "status": "provisioned", "required": True},
            ]
        }
        result = build_setup_readiness(bench_setup)
        d = result.to_dict()
        self.assertIn("overall", d)
        self.assertIn("ready_to_run", d)
        self.assertIn("blocking_issues", d)
        self.assertIn("warnings", d)
        self.assertIn("components", d)
        self.assertEqual(d["overall"], "provisioned_unverified")
        self.assertTrue(d["ready_to_run"])
        self.assertEqual(len(d["components"]), 1)
        self.assertEqual(d["components"][0]["component_id"], "power")

    def test_multiple_blocking_issues_all_reported(self):
        bench_setup = {
            "external_inputs": [
                {"dut_signal": "SIG_A", "kind": "clock", "status": "defined_not_provisioned", "required": True},
                {"dut_signal": "SIG_B", "kind": "power", "status": "manual_loopback_required", "required": True},
            ]
        }
        result = build_setup_readiness(bench_setup)
        self.assertFalse(result.ready_to_run)
        self.assertEqual(len(result.blocking_issues), 2)

    def test_unknown_status_string_defaults_to_provisioned_unverified(self):
        bench_setup = {
            "instrument_roles": [
                {"role": "analyzer", "instrument_id": "la1", "status": "some_unknown_value", "required": True},
            ]
        }
        result = build_setup_readiness(bench_setup)
        self.assertEqual(result.components[0].status, SetupComponentStatus.PROVISIONED_UNVERIFIED)


class TestValidatePowerAndBoot(unittest.TestCase):
    def test_none_returns_empty(self):
        self.assertEqual(validate_power_and_boot(None), [])

    def test_not_dict_returns_error(self):
        errors = validate_power_and_boot("not_a_dict")
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a mapping", errors[0])

    def test_valid_minimal(self):
        errors = validate_power_and_boot({"reset_strategy": "connect_under_reset"})
        self.assertEqual(errors, [])

    def test_invalid_reset_strategy(self):
        errors = validate_power_and_boot({"reset_strategy": "magic_reset"})
        self.assertEqual(len(errors), 1)
        self.assertIn("reset_strategy", errors[0])
        self.assertIn("magic_reset", errors[0])

    def test_invalid_boot_mode(self):
        errors = validate_power_and_boot({"boot_mode_default": "turbo"})
        self.assertEqual(len(errors), 1)
        self.assertIn("boot_mode_default", errors[0])

    def test_valid_all_fields(self):
        errors = validate_power_and_boot({
            "reset_strategy": "pulse_reset",
            "boot_mode_default": "bootloader",
            "power_rails": [
                {"name": "VDD", "nominal_v": 3.3},
            ],
        })
        self.assertEqual(errors, [])

    def test_power_rail_missing_name(self):
        errors = validate_power_and_boot({
            "power_rails": [{"nominal_v": 3.3}],
        })
        self.assertEqual(len(errors), 1)
        self.assertIn("name is required", errors[0])

    def test_power_rail_missing_nominal_v(self):
        errors = validate_power_and_boot({
            "power_rails": [{"name": "VDD"}],
        })
        self.assertEqual(len(errors), 1)
        self.assertIn("nominal_v is required", errors[0])

    def test_power_rail_not_dict(self):
        errors = validate_power_and_boot({
            "power_rails": ["not_a_dict"],
        })
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a mapping", errors[0])

    def test_multiple_power_rails(self):
        errors = validate_power_and_boot({
            "power_rails": [
                {"name": "VDD", "nominal_v": 3.3},
                {"name": "VDDIO", "nominal_v": 1.8},
            ],
        })
        self.assertEqual(errors, [])

    def test_all_valid_reset_strategies(self):
        for strategy in ("connect_under_reset", "pulse_reset", "none"):
            errors = validate_power_and_boot({"reset_strategy": strategy})
            self.assertEqual(errors, [], f"expected no errors for strategy '{strategy}'")

    def test_all_valid_boot_modes(self):
        for mode in ("normal", "bootloader", "isp"):
            errors = validate_power_and_boot({"boot_mode_default": mode})
            self.assertEqual(errors, [], f"expected no errors for boot mode '{mode}'")


if __name__ == "__main__":
    unittest.main()
