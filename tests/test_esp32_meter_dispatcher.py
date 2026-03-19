from __future__ import annotations

from unittest.mock import patch

from ael.instruments.config_loader import InstrumentCatalog
from ael.instruments.dispatcher import run_action


def _catalog() -> InstrumentCatalog:
    return InstrumentCatalog(
        [
            {
                "name": "dut1",
                "role": "dut",
                "attached_instruments": ["meter_1"],
            },
            {
                "name": "meter_1",
                "role": "instrument",
                "driver": "esp32_meter",
                "connection": {"host": "192.168.4.1", "tcp_port": 9000},
                "config": {"voltage_channels": {"vbat": 4}},
                "supports": ["gpio_measure", "voltage_read", "stim_digital"],
            },
        ]
    )


def test_dispatcher_routes_gpio_measure_to_meter_backend():
    catalog = _catalog()
    with patch(
        "ael.adapters.esp32s3_dev_c_meter_tcp.measure_digital",
        return_value={"ok": True, "pins": [11], "duration_ms": 500},
    ):
        out = run_action(dut="dut1", action="gpio_measure", request={"channel": 11}, catalog=catalog)
    assert out["ok"] is True
    assert out["instrument"] == "meter_1"
    assert out["data"]["channels"] == [11]


def test_dispatcher_routes_voltage_read_to_meter_backend():
    catalog = _catalog()
    with patch(
        "ael.adapters.esp32s3_dev_c_meter_tcp.measure_voltage",
        return_value={"ok": True, "data": {"voltage_v": 3.25}},
    ):
        out = run_action(dut="dut1", action="voltage_read", request={"channel": "vbat"}, catalog=catalog)
    assert out["ok"] is True
    assert out["data"]["gpio"] == 4


def test_dispatcher_routes_stim_digital_to_meter_backend():
    catalog = _catalog()
    with patch(
        "ael.adapters.esp32s3_dev_c_meter_tcp.stim_digital",
        return_value={"ok": True, "mode": "toggle"},
    ):
        out = run_action(
            dut="dut1",
            action="stim_digital",
            request={"gpio": 15, "mode": "toggle"},
            catalog=catalog,
        )
    assert out["ok"] is True
    assert out["action"] == "stim_digital"
