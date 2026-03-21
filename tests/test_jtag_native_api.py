from __future__ import annotations

from ael.instruments import jtag_native_api


def _probe_cfg():
    return {
        "instance_id": "esp32jtag_stm32_golden",
        "name": "ESP32JTAG",
        "ip": "192.168.2.109",
        "gdb_port": 4242,
        "communication": {
            "primary": "gdb_remote",
            "surfaces": [
                {"name": "gdb_remote", "endpoint": "192.168.2.109:4242"},
                {"name": "web_api", "endpoint": "https://192.168.2.109:443"},
            ],
        },
        "capability_surfaces": {
            "swd": "gdb_remote",
            "gpio_in": "web_api",
            "reset_out": "web_api",
        },
    }


def test_identify_reports_multi_capability_identity():
    out = jtag_native_api.identify(_probe_cfg())
    assert out["status"] == "ok"
    assert out["data"]["device_type"] == "multi_capability_instrument"
    assert out["data"]["instrument_family"] == "esp32jtag"
    assert out["data"]["instrument_role"] == "control"


def test_get_capabilities_reports_family_groups():
    out = jtag_native_api.get_capabilities(_probe_cfg())
    assert out["status"] == "ok"
    assert "debug_remote" in out["data"]["capability_families"]
    assert "capture_control" in out["data"]["capability_families"]
    assert "preflight" in out["data"]["capability_families"]


def test_get_status_reports_endpoint_domains(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.jtag_native_api._tcp_check",
        lambda endpoint, timeout_s=1.0: {"ok": True, "endpoint": endpoint},
    )
    out = jtag_native_api.get_status(_probe_cfg())
    assert out["status"] == "ok"
    assert out["data"]["health_domains"]["debug_remote"]["ok"] is True
    assert out["data"]["health_domains"]["web_api"]["ok"] is True
    assert out["data"]["health_domains"]["capture"]["ok"] is True
    assert out["data"]["health_domains"]["logic_analyzer"]["ok"] is None


def test_doctor_wraps_preflight(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.jtag_native_api._tcp_check",
        lambda endpoint, timeout_s=1.0: {"ok": True, "endpoint": endpoint},
    )
    monkeypatch.setattr(
        "ael.adapters.preflight.run",
        lambda probe_cfg: (True, {"targets": ["M4"], "logic_analyzer": True}),
    )
    out = jtag_native_api.doctor(_probe_cfg())
    assert out["status"] == "ok"
    assert out["data"]["checks"]["preflight"]["ok"] is True
    assert out["data"]["checks"]["logic_analyzer"]["targets"] == ["M4"]
    assert out["data"]["checks"]["capture_control"]["ok"] is True


def test_preflight_probe_reports_native_success(monkeypatch):
    monkeypatch.setattr(
        "ael.adapters.preflight.run",
        lambda probe_cfg: (True, {"targets": ["M4"], "logic_analyzer": True}),
    )
    out = jtag_native_api.preflight_probe(_probe_cfg())
    assert out["status"] == "ok"
    assert out["data"]["protocol_version"] == jtag_native_api.NATIVE_API_PROTOCOL
    assert out["data"]["preflight"]["targets"] == ["M4"]



def test_native_profile_exposes_family_owned_actions():
    profile = jtag_native_api.native_interface_profile()
    assert "program_firmware" in profile["action_commands"]
    assert "capture_signature" in profile["action_commands"]
    assert "program_firmware" in profile["lifecycle_scope"]["owned_by_native_api"]
    assert "capture_signature" in profile["lifecycle_scope"]["owned_by_native_api"]



def test_get_capabilities_reports_program_and_capture_actions():
    out = jtag_native_api.get_capabilities(_probe_cfg())
    assert out["status"] == "ok"
    assert "firmware_programming" in out["data"]["capability_families"]
    assert "capture_signature" in out["data"]["capability_families"]



def test_program_firmware_delegates_to_control_helper(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.controller_backend.program_firmware",
        lambda probe_cfg, **kwargs: {"status": "ok", "data": {"firmware_path": kwargs["firmware_path"], "family": probe_cfg["instance_id"]}},
    )
    out = jtag_native_api.program_firmware(_probe_cfg(), firmware_path="/tmp/fake.elf")
    assert out["status"] == "ok"
    assert out["data"]["firmware_path"] == "/tmp/fake.elf"
    assert out["data"]["family"] == "esp32jtag_stm32_golden"



def test_capture_signature_delegates_to_control_helper(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.controller_backend.capture_signature",
        lambda probe_cfg, **kwargs: {"status": "ok", "data": {"pin": kwargs["pin"], "family": probe_cfg["instance_id"]}},
    )
    out = jtag_native_api.capture_signature(
        _probe_cfg(),
        pin="P0.0",
        duration_s=1.0,
        expected_hz=1.0,
        min_edges=1,
        max_edges=10,
    )
    assert out["status"] == "ok"
    assert out["data"]["pin"] == "P0.0"
    assert out["data"]["family"] == "esp32jtag_stm32_golden"
