from __future__ import annotations

from ael.instruments import controller_backend


def test_program_firmware_delegates_to_control_native_api(monkeypatch):
    probe_cfg = {"instance_id": "esp32jtag_stm32_golden"}

    monkeypatch.setattr(
        "ael.instruments.control_instrument_native_api.program_firmware",
        lambda cfg, **kwargs: {"status": "ok", "data": {"firmware_path": kwargs["firmware_path"], "instance": cfg["instance_id"]}},
    )

    out = controller_backend.program_firmware(probe_cfg, firmware_path="/tmp/fake.elf")

    assert out["status"] == "ok"
    assert out["data"]["firmware_path"] == "/tmp/fake.elf"
    assert out["data"]["instance"] == "esp32jtag_stm32_golden"


def test_capture_signature_delegates_to_control_native_api(monkeypatch):
    probe_cfg = {"instance_id": "esp32jtag_stm32_golden"}

    monkeypatch.setattr(
        "ael.instruments.control_instrument_native_api.capture_signature",
        lambda cfg, **kwargs: {"status": "ok", "data": {"pin": kwargs["pin"], "instance": cfg["instance_id"]}},
    )

    out = controller_backend.capture_signature(
        probe_cfg,
        pin="P0.0",
        duration_s=1.0,
        expected_hz=1.0,
        min_edges=1,
        max_edges=10,
    )

    assert out["status"] == "ok"
    assert out["data"]["pin"] == "P0.0"
    assert out["data"]["instance"] == "esp32jtag_stm32_golden"
