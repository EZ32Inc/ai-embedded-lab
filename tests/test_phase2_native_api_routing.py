from __future__ import annotations

import tempfile
from pathlib import Path

from ael.adapter_registry import AdapterRegistry


def test_instrument_signature_prefers_native_meter_api(monkeypatch):
    registry = AdapterRegistry()
    adapter = registry.get("check.instrument_signature")

    monkeypatch.setattr(
        "ael.instruments.native_api_dispatch.measure_digital",
        lambda manifest, **kwargs: {"status": "ok", "data": {"pins": [{"gpio": 11, "state": "high", "samples": 10, "ones": 10, "zeros": 0, "transitions": 0}]}}
    )
    monkeypatch.setattr(
        "ael.instruments.native_api_dispatch.measure_voltage",
        lambda manifest, **kwargs: {"status": "ok", "data": {"voltage_v": 1.2}}
    )

    with tempfile.TemporaryDirectory() as td:
        result = adapter.execute(
            {
                "type": "check.instrument_signature",
                "inputs": {
                    "instrument_id": "esp32s3_dev_c_meter",
                    "cfg": {"host": "127.0.0.1", "port": 9000},
                    "links": [{"inst_gpio": 11, "expect": "high", "dut_gpio": "GPIO2"}],
                    "analog_links": [{"inst_adc_gpio": 4, "expect_v_min": 1.0, "expect_v_max": 1.4}],
                    "digital_out": str(Path(td) / "instrument_digital.json"),
                    "verify_out": str(Path(td) / "verify_result.json"),
                    "analog_out": str(Path(td) / "instrument_voltage.json"),
                },
            },
            None,
            None,
        )
    assert result["ok"] is True


def test_signal_verify_uses_control_native_api(monkeypatch):
    registry = AdapterRegistry()
    adapter = registry.get("check.signal_verify")

    monkeypatch.setattr(
        "ael.instruments.native_api_dispatch.capture_signature",
        lambda probe_cfg, **kwargs: {
            "status": "ok",
            "data": {
                "blob": b"fake-capture",
                "edges": 3,
                "high": 5,
                "low": 6,
                "window_s": 0.25,
                "sample_rate_hz": 1_000_000,
                "bit": 0,
                "edge_counts": [3] + [0] * 15,
            },
        },
    )
    monkeypatch.setattr(
        "ael.verification.la_verify.analyze_capture_bytes",
        lambda blob, sample_rate_hz, bit, min_edges=2: {"ok": True, "metrics": {"freq_hz": 1.0, "duty": 0.5}, "reasons": []},
    )

    with tempfile.TemporaryDirectory() as td:
        result = adapter.execute(
            {
                "type": "check.signal_verify",
                "inputs": {
                    "probe_cfg": {"name": "ESP32JTAG", "ip": "192.168.2.98", "gdb_port": 4242},
                    "pin": "P0.0",
                    "duration_s": 1.0,
                    "expected_hz": 1.0,
                    "min_edges": 2,
                    "max_edges": 6,
                    "measure_path": str(Path(td) / "measure.json"),
                    "output_mode": "quiet",
                    "test_limits": {},
                    "verify_prep": {},
                    "led_observe_cfg": {},
                    "recovery_demo": {},
                },
            },
            None,
            {},
        )
    assert result["ok"] is True
