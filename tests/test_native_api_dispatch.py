from pathlib import Path

from ael.instruments.registry import InstrumentRegistry
from ael.instruments import native_api_dispatch


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
