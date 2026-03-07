import unittest
from pathlib import Path
from unittest.mock import patch

from ael import strategy_resolver


class TestStrategyResolver(unittest.TestCase):
    def test_resolve_run_strategy_applies_overrides_and_defaults(self):
        probe_raw = {"probe": {"name": "p1"}, "connection": {"ip": "1.2.3.4", "gdb_port": 4242}}
        board_raw = {"board": {"name": "b1", "default_wiring": {"swd": "P3"}}}
        test_raw = {"build": {"project_dir": "assets_golden/duts/esp32s3_devkit/gpio_signature/firmware"}}

        resolved = strategy_resolver.resolve_run_strategy(
            probe_raw=probe_raw,
            board_raw=board_raw,
            test_raw=test_raw,
            wiring="verify=P0.0",
            request_timeout_s=12.0,
            repo_root=Path("."),
        )

        self.assertEqual(resolved.probe_cfg.get("ip"), "1.2.3.4")
        self.assertEqual(resolved.probe_cfg.get("gdb_port"), 4242)
        self.assertEqual(resolved.timeout_s, 12.0)
        self.assertEqual(resolved.wiring_cfg.get("swd"), "P3")
        self.assertEqual(resolved.wiring_cfg.get("verify"), "P0.0")
        self.assertEqual(resolved.wiring_cfg.get("reset"), "UNKNOWN")
        self.assertEqual(resolved.board_cfg.get("build", {}).get("type"), "idf")

    def test_build_verify_step_uses_meter_path_when_capability_present(self):
        test_raw = {
            "instrument": {"id": "meter1", "tcp": {"host": "192.168.4.1", "port": 9000}},
            "connections": {"dut_to_instrument": [{"inst_gpio": 11, "expect": "high"}]},
        }
        board_cfg = {}
        probe_cfg = {}
        wiring_cfg = {"verify": "P0.0"}

        with patch.object(
            strategy_resolver,
            "resolve_instrument_context",
            return_value=("meter1", {"host": "192.168.4.1", "port": 9000}, {"capabilities": [{"name": "measure.digital"}]}),
        ):
            step = strategy_resolver.build_verify_step(
                test_raw=test_raw,
                board_cfg=board_cfg,
                probe_cfg=probe_cfg,
                wiring_cfg=wiring_cfg,
                artifacts_dir=Path("/tmp"),
                observe_log="/tmp/observe.log",
                output_mode="normal",
                measure_path="/tmp/measure.json",
            )

        self.assertEqual(step.get("name"), "check_meter")
        self.assertEqual(step.get("type"), "check.instrument_signature")


if __name__ == "__main__":
    unittest.main()
