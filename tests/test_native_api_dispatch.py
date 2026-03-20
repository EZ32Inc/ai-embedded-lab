from pathlib import Path

from ael.instruments.registry import InstrumentRegistry
from ael.instruments import native_api_dispatch
from ael.instruments.interfaces.model import normalize_capabilities_result, normalize_doctor_check_entry, normalize_doctor_result, normalize_status_health_entry, normalize_status_result


REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeProvider:
    def __init__(self, *, family: str = "fake", identify_data=None, capabilities_data=None, status_data=None, doctor_data=None, action_payloads=None):
        self.family = family
        self._identify_data = identify_data or {"device_id": family}
        self._capabilities_data = capabilities_data or {"capabilities": {}}
        self._status_data = status_data or {"ok": True}
        self._doctor_data = doctor_data or {"reachable": True}
        self._action_payloads = action_payloads or {}

    def native_interface_profile(self):
        return {"instrument_family": self.family}

    def identify(self, _config):
        return {"status": "ok", "data": self._identify_data}

    def get_capabilities(self, _config):
        return {"status": "ok", "data": self._capabilities_data}

    def get_status(self, _config):
        return {"status": "ok", "data": self._status_data}

    def doctor(self, _config):
        return {"status": "ok", "data": self._doctor_data}

    def invoke_action(self, _config, action, **_kwargs):
        return self._action_payloads.get(
            action,
            {"status": "error", "error": {"code": "unsupported_action", "message": f"unsupported action: {action}", "retryable": False}},
        )



def _manifest(instrument_id: str):
    manifest = InstrumentRegistry().get(instrument_id)
    assert manifest
    return manifest



def test_native_api_dispatch_supports_meter_via_provider(monkeypatch):
    manifest = _manifest("esp32s3_dev_c_meter")
    provider = FakeProvider(
        family="esp32_meter",
        identify_data={"device_id": "esp32s3_dev_c_meter"},
        capabilities_data={"capabilities": {"measure.digital": {}}},
        status_data={"ok": True},
    )
    monkeypatch.setattr("ael.instruments.native_api_dispatch.resolve_manifest_provider", lambda _manifest: provider)
    ident = native_api_dispatch.identify(manifest)
    assert ident["status"] == "ok"
    caps = native_api_dispatch.get_capabilities(manifest)
    assert caps["status"] == "ok"
    payload = native_api_dispatch.get_status(manifest)
    assert payload["status"] == "ok"



def test_native_api_dispatch_rejects_unknown_manifest():
    manifest = {"id": "unknown_instrument", "native_interface": {"instrument_family": "unknown_family"}}
    ident = native_api_dispatch.identify(manifest)
    assert ident["status"] == "error"
    assert ident["error"]["code"] == "native_identify_unsupported"
    caps = native_api_dispatch.get_capabilities(manifest)
    assert caps["status"] == "error"
    assert caps["error"]["code"] == "native_get_capabilities_unsupported"
    payload = native_api_dispatch.doctor(manifest)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "native_doctor_unsupported"



def test_control_native_dispatch_routes_to_provider(monkeypatch):
    provider = FakeProvider(family="esp32jtag", identify_data={"instrument_family": "esp32jtag"})
    monkeypatch.setattr("ael.instruments.native_api_dispatch.resolve_control_provider", lambda _cfg: provider)
    payload = native_api_dispatch.control_identify({"name": "ESP32JTAG"})
    assert payload["status"] == "ok"
    assert payload["data"]["instrument_family"] == "esp32jtag"



def test_control_preflight_routes_to_provider(monkeypatch):
    provider = FakeProvider(
        family="esp32jtag",
        action_payloads={
            "preflight_probe": {"status": "ok", "data": {"protocol_version": "ael.local_instrument.jtag_native_api.v0.1"}}
        },
    )
    monkeypatch.setattr("ael.instruments.native_api_dispatch.resolve_control_provider", lambda _cfg: provider)
    payload = native_api_dispatch.preflight_probe({"name": "ESP32JTAG"})
    assert payload["status"] == "ok"
    assert payload["data"]["protocol_version"] == "ael.local_instrument.jtag_native_api.v0.1"



def test_control_identify_supports_stlink_provider():
    payload = native_api_dispatch.control_identify(
        {
            "type_id": "stlink",
            "instance_id": "stlink_stm32f103_gpio",
            "name": "ST-Link",
            "ip": "127.0.0.1",
            "gdb_port": 4242,
            "communication": {
                "surfaces": [
                    {"name": "gdb_remote", "endpoint": "127.0.0.1:4242"}
                ]
            },
            "capability_surfaces": {"swd": "gdb_remote"},
        }
    )
    assert payload["status"] == "ok"
    assert payload["data"]["instrument_family"] == "stlink"
    assert payload["data"]["instrument_role"] == "control"



def test_native_api_dispatch_supports_usb_uart_manifest_via_provider(monkeypatch):
    manifest = _manifest("usb_uart_bridge_daemon")
    provider = FakeProvider(
        family="usb_uart_bridge",
        identify_data={"device_id": "usb_uart_bridge_daemon", "instrument_family": "usb_uart_bridge"},
        capabilities_data={"capabilities": {"observe.uart": {}}},
        status_data={"bridge_service": True},
        doctor_data={"reachable": True, "checks": {"bridge_service": {"ok": True}}},
    )
    monkeypatch.setattr("ael.instruments.native_api_dispatch.resolve_manifest_provider", lambda _manifest: provider)
    ident = native_api_dispatch.identify(manifest)
    assert ident["status"] == "ok"
    assert ident["data"]["instrument_family"] == "usb_uart_bridge"
    caps = native_api_dispatch.get_capabilities(manifest)
    assert caps["status"] == "ok"
    doctor = native_api_dispatch.doctor(manifest)
    assert doctor["status"] == "ok"


def test_program_firmware_returns_unified_envelope_for_esp32jtag(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.jtag_native_api.program_firmware",
        lambda probe_cfg, **kwargs: {
            "status": "ok",
            "data": {"firmware_path": kwargs["firmware_path"]},
        },
    )
    payload = native_api_dispatch.program_firmware(
        {
            "type_id": "esp32jtag",
            "instance_id": "esp32jtag_lab",
            "ip": "192.168.2.63",
            "gdb_port": 4242,
            "communication": {"surfaces": [{"name": "web_api", "endpoint": "https://192.168.2.63:443"}]},
        },
        firmware_path="/tmp/fw.elf",
    )
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["outcome"] == "success"
    assert payload["family"] == "esp32jtag"
    assert payload["action"] == "program_firmware"
    assert payload["result"]["firmware_path"] == "/tmp/fw.elf"


def test_program_firmware_returns_unified_envelope_for_stlink(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.stlink_native_api.program_firmware",
        lambda probe_cfg, **kwargs: {
            "status": "error",
            "error": {
                "code": "control_program_failed",
                "message": "usb busy",
                "retryable": False,
                "details": {"firmware_path": kwargs["firmware_path"]},
            },
        },
    )
    payload = native_api_dispatch.program_firmware(
        {
            "type_id": "stlink",
            "instance_id": "stlink_gpio",
            "ip": "127.0.0.1",
            "gdb_port": 4242,
            "communication": {"surfaces": [{"name": "gdb_remote", "endpoint": "127.0.0.1:4242"}]},
        },
        firmware_path="/tmp/fw.elf",
    )
    assert payload["status"] == "error"
    assert payload["ok"] is False
    assert payload["outcome"] == "failure"
    assert payload["family"] == "stlink"
    assert payload["action"] == "program_firmware"
    assert payload["error"]["boundary"] == "firmware_programming"
    assert payload["fallback"]["strategy"] == "retry_after_probe_recovery"


def test_control_status_returns_unified_envelope_for_esp32jtag(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.jtag_native_api.get_status",
        lambda probe_cfg: {
            "status": "ok",
            "data": {
                "reachable": True,
                "health_domains": {
                    "network": {"ok": True},
                    "debug_remote": {"ok": True},
                    "web_api": {"ok": True},
                },
                "endpoints": {"debug_remote": {"ok": True, "endpoint": "192.168.2.63:4242"}},
            },
        },
    )
    payload = native_api_dispatch.control_get_status(
        {
            "type_id": "esp32jtag",
            "instance_id": "esp32jtag_lab",
            "ip": "192.168.2.63",
            "gdb_port": 4242,
            "communication": {"surfaces": [{"name": "web_api", "endpoint": "https://192.168.2.63:443"}]},
        }
    )
    assert payload["status"] == "ok"
    assert payload["family"] == "esp32jtag"
    assert payload["action"] == "get_status"
    assert payload["result"]["health"] == "ready"
    assert payload["result"]["status_model_version"] == "instrument_status/v1"
    assert payload["result"]["status_health_schema_version"] == "instrument_status_health/v1"
    assert payload["result"]["status_taxonomy_enforced"] is True
    assert payload["result"]["health_domains"]["network"]["summary"] == "ok"
    assert payload["result"]["health_domains"]["network"]["evidence"] == {}



def test_control_doctor_returns_unified_semantics_for_stlink(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.stlink_native_api.doctor",
        lambda probe_cfg: {
            "status": "ok",
            "data": {
                "reachable": True,
                "checks": {
                    "gdb_remote": {"ok": True},
                    "debug_attach": {"ok": None, "state": "unverified"},
                },
                "lifecycle_boundary": {"owned_by_native_api": ["doctor"]},
            },
        },
    )
    payload = native_api_dispatch.control_doctor(
        {
            "type_id": "stlink",
            "instance_id": "stlink_gpio",
            "ip": "127.0.0.1",
            "gdb_port": 4242,
            "communication": {"surfaces": [{"name": "gdb_remote", "endpoint": "127.0.0.1:4242"}]},
        }
    )
    assert payload["status"] == "ok"
    assert payload["family"] == "stlink"
    assert payload["action"] == "doctor"
    assert payload["result"]["doctor_model_version"] == "instrument_doctor/v1"
    assert payload["result"]["doctor_check_schema_version"] == "instrument_doctor_checks/v1"
    assert payload["result"]["doctor_checks_enforced"] is True
    assert payload["result"]["checks"]["gdb_remote"]["summary"] == "ok"
    assert payload["result"]["checks"]["gdb_remote"]["evidence"] == {}
    assert payload["result"]["checks"]["debug_attach"]["summary"] == "unverified"
    assert payload["result"]["checks"]["debug_attach"]["evidence"]["state"] == "unverified"
    assert payload["result"]["health"] == "healthy"
    assert payload["result"]["failure_boundary"] == "probe_health"



def test_manifest_capabilities_return_unified_taxonomy_for_meter(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.meter_native_api.get_capabilities",
        lambda manifest: {"status": "ok", "data": {"capabilities": {"measure.digital": {}}}},
    )
    payload = native_api_dispatch.get_capabilities(_manifest("esp32s3_dev_c_meter"))
    assert payload["status"] == "ok"
    assert payload["family"] == "esp32_meter"
    assert payload["action"] == "get_capabilities"
    assert payload["result"]["capability_taxonomy_version"] == "instrument_capabilities/v1"
    assert payload["result"]["capability_taxonomy_enforced"] is True
    assert "measure.digital" in payload["result"]["capability_keys"]


def test_capture_signature_returns_unified_envelope_for_esp32jtag(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.jtag_native_api.capture_signature",
        lambda probe_cfg, **kwargs: {
            "status": "ok",
            "data": {"pin": kwargs["pin"], "edges": 8, "high": 100, "low": 120, "blob": b"x"},
        },
    )
    payload = native_api_dispatch.capture_signature(
        {
            "type_id": "esp32jtag",
            "instance_id": "esp32jtag_lab",
            "ip": "192.168.2.63",
            "gdb_port": 4242,
            "communication": {"surfaces": [{"name": "web_api", "endpoint": "https://192.168.2.63:443"}]},
        },
        pin="P0.0",
        duration_s=1.0,
        expected_hz=1000.0,
        min_edges=2,
        max_edges=20,
    )
    assert payload["status"] == "ok"
    assert payload["family"] == "esp32jtag"
    assert payload["action"] == "capture_signature"
    assert payload["result"]["edge_count"] == 8
    assert payload["result"]["edges"] == 8
    assert payload["data"]["edges"] == 8
    assert payload["result"]["capture_blob_present"] is True
    assert payload["fallback"]["strategy"] == "rerun_capture_after_preflight"



def test_capture_signature_returns_unified_unsupported_for_stlink():
    payload = native_api_dispatch.capture_signature(
        {
            "type_id": "stlink",
            "instance_id": "stlink_gpio",
            "ip": "127.0.0.1",
            "gdb_port": 4242,
            "communication": {"surfaces": [{"name": "gdb_remote", "endpoint": "127.0.0.1:4242"}]},
        },
        pin="P0.0",
        duration_s=1.0,
        expected_hz=1000.0,
        min_edges=2,
        max_edges=20,
    )
    assert payload["status"] == "error"
    assert payload["outcome"] == "unsupported"
    assert payload["family"] == "stlink"
    assert payload["action"] == "capture_signature"
    assert payload["error"]["code"] == "control_capture_signature_unsupported"
    assert "program_firmware" in payload["error"]["details"]["supported_actions"]
    assert payload["fallback"]["strategy"] == "choose_supported_instrument"


def test_measure_digital_returns_unified_envelope_for_meter(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.meter_native_api.measure_digital",
        lambda manifest, **kwargs: {
            "status": "ok",
            "data": {"pins": [{"gpio": 11, "state": "toggle", "transitions": 9}], "duration_ms": kwargs["duration_ms"]},
        },
    )
    payload = native_api_dispatch.measure_digital(
        _manifest("esp32s3_dev_c_meter"),
        pins=[11],
        duration_ms=250,
    )
    assert payload["status"] == "ok"
    assert payload["family"] == "esp32_meter"
    assert payload["action"] == "measure_digital"
    assert payload["result"]["measurement_kind"] == "digital"
    assert payload["result"]["pins"][0]["gpio"] == 11
    assert payload["data"]["pins"][0]["gpio"] == 11



def test_measure_voltage_returns_unified_envelope_for_meter(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.meter_native_api.measure_voltage",
        lambda manifest, **kwargs: {
            "status": "ok",
            "data": {"gpio": kwargs["gpio"], "avg": kwargs["avg"], "voltage_v": 3.31},
        },
    )
    payload = native_api_dispatch.measure_voltage(
        _manifest("esp32s3_dev_c_meter"),
        gpio=4,
        avg=8,
    )
    assert payload["status"] == "ok"
    assert payload["family"] == "esp32_meter"
    assert payload["action"] == "measure_voltage"
    assert payload["result"]["measurement_kind"] == "voltage"
    assert payload["result"]["voltage_v"] == 3.31
    assert payload["data"]["voltage_v"] == 3.31



def test_stim_digital_returns_unified_envelope_for_meter(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.meter_native_api.stim_digital",
        lambda manifest, **kwargs: {
            "status": "ok",
            "data": {
                "gpio": kwargs["gpio"],
                "mode": kwargs["mode"],
                "duration_us": kwargs["duration_us"],
                "keep": kwargs["keep"],
            },
        },
    )
    payload = native_api_dispatch.stim_digital(
        _manifest("esp32s3_dev_c_meter"),
        gpio=15,
        mode="toggle",
        duration_us=500,
        keep=1,
    )
    assert payload["status"] == "ok"
    assert payload["family"] == "esp32_meter"
    assert payload["action"] == "stim_digital"
    assert payload["result"]["stimulus_kind"] == "digital"
    assert payload["result"]["gpio"] == 15
    assert payload["result"]["mode"] == "toggle"
    assert payload["result"]["keep"] == 1
    assert payload["data"]["gpio"] == 15
    assert payload["data"]["mode"] == "toggle"


def test_normalize_capabilities_rejects_unknown_taxonomy_key():
    try:
        normalize_capabilities_result(
            family="fake",
            capabilities={"legacy.capability": {"actions": ["noop"], "surfaces": ["legacy"]}},
        )
    except ValueError as exc:
        assert "unknown capability taxonomy key" in str(exc)
    else:
        raise AssertionError("expected capability taxonomy enforcement failure")


def test_normalize_status_rejects_unknown_health_domain_key():
    try:
        normalize_status_result(
            family="fake",
            reachable=True,
            health_domains={"legacy_domain": {"ok": True}},
        )
    except ValueError as exc:
        assert "unknown status health-domain key" in str(exc)
    else:
        raise AssertionError("expected status taxonomy enforcement failure")


def test_normalize_doctor_rejects_unknown_check_key():
    try:
        normalize_doctor_result(
            family="fake",
            reachable=True,
            checks={"legacy_check": {"ok": True}},
        )
    except ValueError as exc:
        assert "unknown doctor check key" in str(exc)
    else:
        raise AssertionError("expected doctor taxonomy enforcement failure")


def test_normalize_doctor_check_entry_canonicalizes_summary_detail_and_evidence():
    payload = normalize_doctor_check_entry(
        "preflight",
        {"ok": False, "error": "timeout", "attempts": 2},
    )
    assert payload["ok"] is False
    assert payload["summary"] == "timeout"
    assert payload["detail"] == "timeout"
    assert payload["evidence"]["error"] == "timeout"
    assert payload["evidence"]["attempts"] == 2


def test_normalize_status_health_entry_canonicalizes_summary_detail_and_evidence():
    payload = normalize_status_health_entry(
        "network",
        {"ok": False, "error": "unreachable", "endpoint": "10.0.0.8"},
    )
    assert payload["ok"] is False
    assert payload["summary"] == "unreachable"
    assert payload["detail"] == "unreachable"
    assert payload["evidence"]["error"] == "unreachable"
    assert payload["evidence"]["endpoint"] == "10.0.0.8"
