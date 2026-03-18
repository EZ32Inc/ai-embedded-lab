from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ael.instruments.config_loader import InstrumentCatalog
from ael.instruments.dispatcher import run_action


def _catalog() -> InstrumentCatalog:
    return InstrumentCatalog(
        [
            {
                "name": "dut1",
                "role": "dut",
                "attached_instruments": ["esp32_jtag_1"],
            },
            {
                "name": "esp32_jtag_1",
                "role": "instrument",
                "driver": "esp32_jtag",
                "connection": {"host": "192.168.1.50", "port": 5555},
                "supports": ["flash", "gpio_measure", "reset"],
            },
        ]
    )


def test_dispatcher_routes_reset_to_esp32_jtag_backend():
    catalog = _catalog()
    fake_response = {"ok": True, "elapsed_s": 0.2, "method": "hard_line", "logs": ["reset ok"]}
    with patch(
        "ael.instruments.backends.esp32_jtag.transport.Esp32JtagTransport.request",
        return_value=fake_response,
    ) as mock_request:
        out = run_action(dut="dut1", action="reset", request={"reset_kind": "hard"}, catalog=catalog)
    assert out["ok"] is True
    assert out["instrument"] == "esp32_jtag_1"
    assert out["dut"] == "dut1"
    assert out["action"] == "reset"
    assert out["data"]["method"] == "hard_line"
    mock_request.assert_called_once_with(command="reset", payload={"reset_kind": "hard"})


def test_dispatcher_rejects_invalid_reset_kind_from_esp32_jtag_backend():
    catalog = _catalog()
    out = run_action(dut="dut1", action="reset", request={"reset_kind": "bad"}, catalog=catalog)
    assert out["ok"] is False
    assert out["error_code"] == "invalid_request"
    assert "reset_kind must be one of" in out["message"]


def test_dispatcher_reports_no_instrument_for_unsupported_action():
    catalog = _catalog()
    out = run_action(dut="dut1", action="uart_read", request={}, catalog=catalog)
    assert out["ok"] is False
    assert out["error_code"] == "no_instrument_available"


def test_backend_reports_structured_unsupported_action_when_called_directly():
    from ael.instruments.backends.esp32_jtag.backend import Esp32JtagBackend

    backend = Esp32JtagBackend(host="127.0.0.1", port=5555)
    out = backend.execute("flash", {})
    assert out["status"] == "failure"
    assert out["action"] == "flash"
    assert out["error"]["code"] == "invalid_request"


def test_dispatcher_routes_flash_to_esp32_jtag_backend(tmp_path: Path):
    catalog = _catalog()
    firmware = tmp_path / "app.elf"
    firmware.write_text("fake", encoding="utf-8")
    fake_response = {
        "ok": True,
        "bytes_written": 1234,
        "elapsed_s": 1.2,
        "verified": True,
        "logs": ["flash ok"],
    }
    with patch(
        "ael.instruments.backends.esp32_jtag.transport.Esp32JtagTransport.request",
        return_value=fake_response,
    ) as mock_request:
        out = run_action(
            dut="dut1",
            action="flash",
            request={"firmware": str(firmware)},
            catalog=catalog,
        )
    assert out["ok"] is True
    assert out["action"] == "flash"
    assert out["data"]["firmware_path"] == str(firmware)
    mock_request.assert_called_once_with(
        command="flash",
        payload={"firmware_path": str(firmware), "target": None, "options": {}},
    )


def test_dispatcher_rejects_invalid_flash_path_from_esp32_jtag_backend():
    catalog = _catalog()
    out = run_action(
        dut="dut1",
        action="flash",
        request={"firmware": "/tmp/does-not-exist.elf"},
        catalog=catalog,
    )
    assert out["ok"] is False
    assert out["error_code"] == "invalid_request"
    assert "firmware image does not exist" in out["message"]


def test_dispatcher_routes_gpio_measure_to_esp32_jtag_backend():
    catalog = _catalog()
    fake_response = {
        "ok": True,
        "values": {"PA0": {"freq_hz": 1000}},
        "summary": "signature ok",
        "pass_hint": True,
        "elapsed_s": 0.3,
        "logs": ["measure ok"],
    }
    with patch(
        "ael.instruments.backends.esp32_jtag.transport.Esp32JtagTransport.request",
        return_value=fake_response,
    ) as mock_request:
        out = run_action(
            dut="dut1",
            action="gpio_measure",
            request={"channel": "PA0"},
            catalog=catalog,
        )
    assert out["ok"] is True
    assert out["action"] == "gpio_measure"
    assert out["data"]["channels"] == ["PA0"]
    assert out["data"]["summary"] == "signature ok"
    mock_request.assert_called_once_with(
        command="gpio_measure",
        payload={"channels": ["PA0"], "measurement_type": "signature", "settle_ms": 0},
    )
