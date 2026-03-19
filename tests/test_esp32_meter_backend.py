from __future__ import annotations

from unittest.mock import patch

from ael.instruments.backends.esp32_meter.backend import Esp32MeterBackend, invoke


def _instrument() -> dict:
    return {
        "name": "meter_1",
        "driver": "esp32_meter",
        "connection": {"host": "192.168.4.1", "tcp_port": 9000},
        "config": {"duration_ms": 250, "voltage_channels": {"vbat": 4}},
    }


def test_meter_backend_reports_structured_gpio_measure_success():
    backend = Esp32MeterBackend(host="192.168.4.1", port=9000)
    with patch(
        "ael.adapters.esp32s3_dev_c_meter_tcp.measure_digital",
        return_value={"ok": True, "pins": [11], "duration_ms": 250},
    ):
        out = backend.execute("gpio_measure", {"channels": [11], "duration_ms": 250})
    assert out["status"] == "success"
    assert out["action"] == "gpio_measure"
    assert out["data"]["channels"] == [11]


def test_meter_backend_reports_structured_voltage_read_success():
    backend = Esp32MeterBackend(host="192.168.4.1", port=9000)
    with patch(
        "ael.adapters.esp32s3_dev_c_meter_tcp.measure_voltage",
        return_value={"ok": True, "data": {"voltage_v": 3.3}},
    ):
        out = backend.execute("voltage_read", {"gpio": 4, "avg": 8})
    assert out["status"] == "success"
    assert out["data"]["voltage_v"] == 3.3


def test_meter_backend_reports_structured_stim_success():
    backend = Esp32MeterBackend(host="192.168.4.1", port=9000)
    with patch(
        "ael.adapters.esp32s3_dev_c_meter_tcp.stim_digital",
        return_value={"ok": True, "mode": "toggle"},
    ):
        out = backend.execute("stim_digital", {"gpio": 15, "mode": "toggle"})
    assert out["status"] == "success"
    assert out["action"] == "stim_digital"


def test_meter_backend_reports_invalid_request():
    backend = Esp32MeterBackend(host="192.168.4.1", port=9000)
    out = backend.execute("voltage_read", {})
    assert out["status"] == "failure"
    assert out["error"]["code"] == "invalid_request"


def test_meter_invoke_bridges_gpio_measure_request_shape():
    with patch(
        "ael.adapters.esp32s3_dev_c_meter_tcp.measure_digital",
        return_value={"ok": True, "pins": [11], "duration_ms": 500},
    ):
        out = invoke("gpio_measure", _instrument(), {"channel": 11}, {"dut": "dut1"})
    assert out["ok"] is True
    assert out["action"] == "gpio_measure"
    assert out["data"]["channels"] == [11]


def test_meter_invoke_bridges_voltage_channel_mapping():
    with patch(
        "ael.adapters.esp32s3_dev_c_meter_tcp.measure_voltage",
        return_value={"ok": True, "data": {"voltage_v": 3.2}},
    ):
        out = invoke("voltage_read", _instrument(), {"channel": "vbat"}, {"dut": "dut1"})
    assert out["ok"] is True
    assert out["data"]["gpio"] == 4

