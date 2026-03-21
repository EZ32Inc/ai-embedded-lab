from __future__ import annotations

from ael.instruments.interfaces import stlink, esp32jtag


def _stlink_cfg():
    return {
        "type_id": "stlink",
        "instance_id": "stlink_test",
        "ip": "127.0.0.1",
        "gdb_port": 4242,
        "communication": {"surfaces": [{"name": "gdb_remote", "endpoint": "127.0.0.1:4242"}]},
        "capability_surfaces": {"swd": "gdb_remote"},
    }


def _jtag_cfg():
    return {
        "type_id": "esp32jtag",
        "instance_id": "jtag_test",
        "ip": "192.168.2.109",
        "gdb_port": 4242,
        "communication": {
            "surfaces": [
                {"name": "gdb_remote", "endpoint": "192.168.2.109:4242"},
                {"name": "web_api", "endpoint": "https://192.168.2.109:443"},
            ]
        },
        "capability_surfaces": {"swd": "gdb_remote", "gpio_in": "web_api", "reset_out": "web_api"},
    }


def test_stlink_preflight_probe_emits_model_v1_envelope(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.stlink_native_api.preflight_probe",
        lambda cfg: {"status": "ok", "data": {"protocol_version": "v0.1", "preflight": {"gdb_remote": {"ok": True}}}},
    )
    result = stlink._preflight_probe(_stlink_cfg())
    assert result["ok"] is True
    assert result["outcome"] == "success"
    assert result["action"] == "preflight_probe"
    assert result["family"] == "stlink"
    assert result["result"]["transport"] == "gdb_remote"
    assert result["result"]["gdb_remote"]["ok"] is True


def test_stlink_preflight_probe_failure_emits_model_v1_envelope(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.stlink_native_api.preflight_probe",
        lambda cfg: {"status": "error", "error": {"code": "stlink_preflight_failed", "message": "unreachable", "retryable": True}},
    )
    result = stlink._preflight_probe(_stlink_cfg())
    assert result["ok"] is False
    assert result["outcome"] == "failure"
    assert result["action"] == "preflight_probe"
    assert result["family"] == "stlink"
    assert result["error"]["code"] == "stlink_preflight_failed"
    assert result["fallback"]["strategy"] == "retry_after_probe_recovery"


def test_esp32jtag_preflight_probe_emits_model_v1_envelope(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.jtag_native_api.preflight_probe",
        lambda cfg: {
            "status": "ok",
            "data": {
                "protocol_version": "v0.1",
                "preflight": {"targets": ["M4"], "monitor_ok": True, "la_ok": True},
            },
        },
    )
    result = esp32jtag._preflight_probe(_jtag_cfg())
    assert result["ok"] is True
    assert result["outcome"] == "success"
    assert result["action"] == "preflight_probe"
    assert result["family"] == "esp32jtag"
    assert result["result"]["transport"] == "gdb_remote"
    assert result["result"]["targets"] == ["M4"]
    assert result["result"]["monitor_ok"] is True
    assert result["result"]["logic_analyzer_ok"] is True


def test_esp32jtag_preflight_probe_failure_emits_model_v1_envelope(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.jtag_native_api.preflight_probe",
        lambda cfg: {"status": "error", "error": {"code": "jtag_preflight_failed", "message": "preflight failed", "retryable": True}},
    )
    result = esp32jtag._preflight_probe(_jtag_cfg())
    assert result["ok"] is False
    assert result["outcome"] == "failure"
    assert result["action"] == "preflight_probe"
    assert result["family"] == "esp32jtag"
    assert result["error"]["code"] == "jtag_preflight_failed"
    assert result["fallback"]["strategy"] == "rerun_preflight_then_retry"
