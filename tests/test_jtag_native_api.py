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


def test_get_capabilities_reports_family_groups():
    out = jtag_native_api.get_capabilities(_probe_cfg())
    assert out["status"] == "ok"
    assert "debug_remote" in out["data"]["capability_families"]
    assert "capture_control" in out["data"]["capability_families"]


def test_get_status_reports_endpoint_domains(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.jtag_native_api._tcp_check",
        lambda endpoint, timeout_s=1.0: {"ok": True, "endpoint": endpoint},
    )
    out = jtag_native_api.get_status(_probe_cfg())
    assert out["status"] == "ok"
    assert out["data"]["health_domains"]["debug_remote"]["ok"] is True
    assert out["data"]["health_domains"]["capture_control"]["ok"] is True


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


def test_preflight_probe_reports_native_success(monkeypatch):
    monkeypatch.setattr(
        "ael.adapters.preflight.run",
        lambda probe_cfg: (True, {"targets": ["M4"], "logic_analyzer": True}),
    )
    out = jtag_native_api.preflight_probe(_probe_cfg())
    assert out["status"] == "ok"
    assert out["data"]["protocol_version"] == jtag_native_api.NATIVE_API_PROTOCOL
    assert out["data"]["preflight"]["targets"] == ["M4"]
