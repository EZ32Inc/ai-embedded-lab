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
        "ael.instruments.meter_native_api.get_status",
        lambda manifest: {"status": "ok", "data": {"ok": True}},
    )
    payload = native_api_dispatch.get_status(manifest)
    assert payload["status"] == "ok"


def test_native_api_dispatch_rejects_unsupported_manifest():
    manifest = _manifest("usb_uart_bridge_daemon")
    payload = native_api_dispatch.doctor(manifest)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "native_doctor_unsupported"
