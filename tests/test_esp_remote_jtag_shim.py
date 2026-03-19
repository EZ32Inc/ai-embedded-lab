from __future__ import annotations

from unittest.mock import patch

from ael.instruments.backends import esp_remote_jtag


def _instrument():
    return {
        "name": "legacy_remote_1",
        "driver": "esp_remote_jtag",
        "connection": {"host": "192.168.2.50", "gdb_port": 4242, "web_port": 9000},
        "config": {"target_id": 1},
    }


def test_legacy_shim_routes_flash_to_esp32_jtag():
    with patch(
        "ael.instruments.backends.esp32_jtag.backend.invoke",
        return_value={"ok": True, "action": "flash"},
    ) as invoke:
        out = esp_remote_jtag.invoke("flash", _instrument(), {"firmware_path": "app.elf"}, {"dut": "dut1"})
    assert out["ok"] is True
    invoke.assert_called_once()


def test_legacy_shim_routes_voltage_read_to_esp32_meter():
    with patch(
        "ael.instruments.backends.esp32_meter.backend.invoke",
        return_value={"ok": True, "action": "voltage_read"},
    ) as invoke:
        out = esp_remote_jtag.invoke("voltage_read", _instrument(), {"channel": 4}, {"dut": "dut1"})
    assert out["ok"] is True
    translated_instrument = invoke.call_args[0][1]
    assert translated_instrument["driver"] == "esp32_meter"
    assert translated_instrument["connection"]["tcp_port"] == 9000
