from __future__ import annotations

from ael.instruments import controller_backend


def test_program_firmware_calls_flash_adapter(monkeypatch):
    probe_cfg = {"instance_id": "esp32jtag_stm32_golden"}
    calls = {}

    def fake_flash_run(cfg, firmware_path, *, flash_cfg, flash_json_path):
        calls["cfg"] = cfg
        calls["firmware_path"] = firmware_path
        return True

    monkeypatch.setattr("ael.instruments.controller_backend.flash_bmda_gdbmi.run", fake_flash_run)

    out = controller_backend.program_firmware(probe_cfg, firmware_path="/tmp/fake.elf")

    assert out["status"] == "ok"
    assert out["data"]["firmware_path"] == "/tmp/fake.elf"
    assert calls["firmware_path"] == "/tmp/fake.elf"
    assert calls["cfg"]["instance_id"] == "esp32jtag_stm32_golden"


def test_program_firmware_returns_error_on_flash_failure(monkeypatch):
    probe_cfg = {"instance_id": "esp32jtag_stm32_golden"}

    monkeypatch.setattr(
        "ael.instruments.controller_backend.flash_bmda_gdbmi.run",
        lambda *a, **kw: False,
    )

    out = controller_backend.program_firmware(probe_cfg, firmware_path="/tmp/fake.elf")

    assert out["status"] == "error"
    assert out["error"]["code"] == "control_program_failed"


def test_capture_signature_calls_gpio_adapter(monkeypatch):
    probe_cfg = {"instance_id": "esp32jtag_stm32_golden"}
    calls = {}

    def fake_gpio_run(cfg, *, pin, pins, duration_s, expected_hz, min_edges, max_edges, capture_out, verify_edges):
        calls["pin"] = pin
        calls["cfg"] = cfg
        capture_out["edges"] = 4
        capture_out["high"] = 2
        capture_out["low"] = 2
        return True

    monkeypatch.setattr("ael.instruments.controller_backend.observe_gpio_pin.run", fake_gpio_run)

    out = controller_backend.capture_signature(
        probe_cfg,
        pin="P0.0",
        duration_s=1.0,
        expected_hz=1.0,
        min_edges=1,
        max_edges=10,
    )

    assert out["status"] == "ok"
    assert out["data"]["edges"] == 4
    assert calls["pin"] == "P0.0"
    assert calls["cfg"]["instance_id"] == "esp32jtag_stm32_golden"


def test_capture_signature_returns_error_on_gpio_failure(monkeypatch):
    probe_cfg = {"instance_id": "esp32jtag_stm32_golden"}

    monkeypatch.setattr(
        "ael.instruments.controller_backend.observe_gpio_pin.run",
        lambda *a, **kw: False,
    )

    out = controller_backend.capture_signature(
        probe_cfg,
        pin="P0.0",
        duration_s=1.0,
        expected_hz=1.0,
        min_edges=1,
        max_edges=10,
    )

    assert out["status"] == "error"
    assert out["error"]["code"] == "capture_signature_failed"
