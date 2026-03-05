import tempfile
import unittest
from pathlib import Path

from ael.adapter_registry import AdapterRegistry


class _FakeBackend:
    def __init__(self):
        self.calls = []

    def selftest(self, cfg, params, out_path):
        self.calls.append(("selftest", cfg, params, out_path))
        return {"pass": True}

    def measure_digital(self, cfg, pins, duration_ms, out_path):
        self.calls.append(("measure.digital", cfg, pins, duration_ms, out_path))
        return {
            "pins": [
                {"gpio": int(pins[0]), "state": "high", "samples": 100, "ones": 100, "zeros": 0, "transitions": 0},
            ]
        }

    def measure_voltage(self, cfg, gpio, avg, out_path):
        self.calls.append(("measure.voltage", cfg, gpio, avg, out_path))
        return {"voltage_v": 1.2}


class _FakeBackendRegistry:
    def __init__(self, backend):
        self.backend = backend
        self.resolve_calls = []

    def resolve(self, instrument_id, capability):
        self.resolve_calls.append((instrument_id, capability))
        return self.backend


class TestInstrumentBackendRouting(unittest.TestCase):
    def test_selftest_routes_with_instrument_id(self):
        registry = AdapterRegistry()
        adapter = registry.get("check.instrument_selftest")
        fake_backend = _FakeBackend()
        fake_registry = _FakeBackendRegistry(fake_backend)
        adapter._backend_registry = fake_registry

        with tempfile.TemporaryDirectory() as td:
            out_path = str(Path(td) / "instrument_selftest.json")
            result = adapter.execute(
                {
                    "type": "check.instrument_selftest",
                    "inputs": {
                        "instrument_id": "esp32s3_dev_c_meter",
                        "cfg": {"host": "127.0.0.1", "port": 9000},
                        "params": {"out_gpio": 15},
                        "out_path": out_path,
                    },
                },
                None,
                None,
            )
        self.assertTrue(result.get("ok"))
        self.assertEqual(fake_registry.resolve_calls, [("esp32s3_dev_c_meter", "selftest")])

    def test_signature_routes_digital_and_voltage_capabilities(self):
        registry = AdapterRegistry()
        adapter = registry.get("check.instrument_signature")
        fake_backend = _FakeBackend()
        fake_registry = _FakeBackendRegistry(fake_backend)
        adapter._backend_registry = fake_registry

        with tempfile.TemporaryDirectory() as td:
            digital_out = str(Path(td) / "instrument_digital.json")
            verify_out = str(Path(td) / "verify_result.json")
            analog_out = str(Path(td) / "instrument_voltage.json")
            result = adapter.execute(
                {
                    "type": "check.instrument_signature",
                    "inputs": {
                        "instrument_id": "esp32s3_dev_c_meter",
                        "cfg": {"host": "127.0.0.1", "port": 9000},
                        "links": [{"inst_gpio": 11, "expect": "high", "dut_gpio": "GPIO2"}],
                        "analog_links": [{"inst_adc_gpio": 4, "expect_v_min": 1.0, "expect_v_max": 1.4}],
                        "digital_out": digital_out,
                        "verify_out": verify_out,
                        "analog_out": analog_out,
                        "duration_ms": 500,
                    },
                },
                None,
                None,
            )
        self.assertTrue(result.get("ok"))
        self.assertEqual(
            fake_registry.resolve_calls,
            [
                ("esp32s3_dev_c_meter", "measure.digital"),
                ("esp32s3_dev_c_meter", "measure.voltage"),
            ],
        )

    def test_signature_unknown_instrument_reports_error(self):
        registry = AdapterRegistry()
        adapter = registry.get("check.instrument_signature")
        with tempfile.TemporaryDirectory() as td:
            result = adapter.execute(
                {
                    "type": "check.instrument_signature",
                    "inputs": {
                        "instrument_id": "unknown_instrument",
                        "cfg": {"host": "127.0.0.1", "port": 9000},
                        "links": [{"inst_gpio": 11, "expect": "high"}],
                        "digital_out": str(Path(td) / "instrument_digital.json"),
                        "verify_out": str(Path(td) / "verify_result.json"),
                    },
                },
                None,
                None,
            )
        self.assertFalse(result.get("ok"))
        self.assertIn("instrument backend not found for id", str(result.get("error_summary")))


if __name__ == "__main__":
    unittest.main()
