from pathlib import Path

from ael.instruments.registry import InstrumentRegistry
from ael.instruments import native_api_dispatch


REPO_ROOT = Path(__file__).resolve().parents[1]


def _manifest(instrument_id: str):
    manifest = InstrumentRegistry().get(instrument_id)
    assert manifest
    return manifest


def test_native_api_dispatch_supports_meter(monkeypatch):
    manifest = _manifest("esp32s3_dev_c_meter")
    monkeypatch.setattr(
        "ael.instruments.meter_native_api.identify",
        lambda manifest: {"status": "ok", "data": {"device_id": "esp32s3_dev_c_meter"}},
    )
    monkeypatch.setattr(
        "ael.instruments.meter_native_api.get_capabilities",
        lambda manifest: {"status": "ok", "data": {"capabilities": {"measure.digital": {}}}},
    )
    monkeypatch.setattr(
        "ael.instruments.meter_native_api.get_status",
        lambda manifest: {"status": "ok", "data": {"ok": True}},
    )
    ident = native_api_dispatch.identify(manifest)
    assert ident["status"] == "ok"
    caps = native_api_dispatch.get_capabilities(manifest)
    assert caps["status"] == "ok"
    payload = native_api_dispatch.get_status(manifest)
    assert payload["status"] == "ok"


def test_native_api_dispatch_rejects_unsupported_manifest():
    manifest = _manifest("usb_uart_bridge_daemon")
    ident = native_api_dispatch.identify(manifest)
    assert ident["status"] == "error"
    assert ident["error"]["code"] == "native_identify_unsupported"
    caps = native_api_dispatch.get_capabilities(manifest)
    assert caps["status"] == "error"
    assert caps["error"]["code"] == "native_get_capabilities_unsupported"
    payload = native_api_dispatch.doctor(manifest)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "native_doctor_unsupported"


def test_control_native_dispatch_routes_to_jtag_native_api(monkeypatch):
    monkeypatch.setattr(
        "ael.instruments.jtag_native_api.identify",
        lambda probe_cfg: {"status": "ok", "data": {"instrument_family": "esp32jtag"}},
    )
    payload = native_api_dispatch.control_identify({"name": "ESP32JTAG"})
    assert payload["status"] == "ok"
    assert payload["data"]["instrument_family"] == "esp32jtag"
