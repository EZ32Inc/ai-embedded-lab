from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ael.instruments.backends.esp32_jtag.backend import Esp32JtagBackend
from ael.instruments.backends.esp32_jtag.errors import TransportUnavailable


def test_backend_returns_structured_reset_success():
    backend = Esp32JtagBackend(host="127.0.0.1", port=5555)
    with patch(
        "ael.instruments.backends.esp32_jtag.transport.Esp32JtagTransport.request",
        return_value={"ok": True, "elapsed_s": 0.1, "method": "hard_line", "logs": ["ok"]},
    ):
        out = backend.execute("reset", {"reset_kind": "hard"})
    assert out["status"] == "success"
    assert out["action"] == "reset"
    assert out["data"]["method"] == "hard_line"
    assert out["logs"] == ["ok"]


def test_backend_returns_structured_invalid_request_for_bad_reset_kind():
    backend = Esp32JtagBackend(host="127.0.0.1", port=5555)
    out = backend.execute("reset", {"reset_kind": "bad"})
    assert out["status"] == "failure"
    assert out["action"] == "reset"
    assert out["error"]["code"] == "invalid_request"
    assert "reset_kind must be one of" in out["error"]["message"]
    assert out["error"]["details"]["exception_type"] == "InvalidRequest"


def test_backend_returns_structured_flash_success(tmp_path: Path):
    backend = Esp32JtagBackend(host="127.0.0.1", port=5555)
    firmware = tmp_path / "app.elf"
    firmware.write_text("fake", encoding="utf-8")
    with patch(
        "ael.instruments.backends.esp32_jtag.transport.Esp32JtagTransport.request",
        return_value={"ok": True, "bytes_written": 123, "elapsed_s": 1.0, "verified": True},
    ):
        out = backend.execute("flash", {"firmware_path": str(firmware)})
    assert out["status"] == "success"
    assert out["action"] == "flash"
    assert out["data"]["firmware_path"] == str(firmware)
    assert out["data"]["verified"] is True


def test_backend_returns_structured_invalid_request_for_missing_flash_file():
    backend = Esp32JtagBackend(host="127.0.0.1", port=5555)
    out = backend.execute("flash", {"firmware_path": "/tmp/nope.elf"})
    assert out["status"] == "failure"
    assert out["action"] == "flash"
    assert out["error"]["code"] == "invalid_request"
    assert "firmware image does not exist" in out["error"]["message"]


def test_backend_returns_structured_gpio_measure_success():
    backend = Esp32JtagBackend(host="127.0.0.1", port=5555)
    with patch(
        "ael.instruments.backends.esp32_jtag.transport.Esp32JtagTransport.request",
        return_value={
            "ok": True,
            "values": {"PA0": {"freq_hz": 1000}},
            "summary": "signature ok",
            "pass_hint": True,
            "elapsed_s": 0.2,
        },
    ):
        out = backend.execute("gpio_measure", {"channels": ["PA0"]})
    assert out["status"] == "success"
    assert out["action"] == "gpio_measure"
    assert out["data"]["channels"] == ["PA0"]
    assert out["data"]["summary"] == "signature ok"


def test_backend_returns_structured_invalid_request_for_missing_gpio_channels():
    backend = Esp32JtagBackend(host="127.0.0.1", port=5555)
    out = backend.execute("gpio_measure", {})
    assert out["status"] == "failure"
    assert out["action"] == "gpio_measure"
    assert out["error"]["code"] == "invalid_request"
    assert "requires non-empty 'channels' list" in out["error"]["message"]


def test_backend_returns_structured_transport_failure():
    backend = Esp32JtagBackend(host="127.0.0.1", port=5555)
    with patch(
        "ael.instruments.backends.esp32_jtag.transport.Esp32JtagTransport.request",
        side_effect=TransportUnavailable("cannot connect"),
    ):
        out = backend.execute("reset", {"reset_kind": "hard"})
    assert out["status"] == "failure"
    assert out["action"] == "reset"
    assert out["error"]["code"] == "transport_unavailable"
    assert out["error"]["details"]["exception_type"] == "TransportUnavailable"
