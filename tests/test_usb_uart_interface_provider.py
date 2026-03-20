from __future__ import annotations

from ael.instruments.interfaces import usb_uart_bridge
from ael.instruments.registry import InstrumentRegistry



def _manifest():
    manifest = InstrumentRegistry().get("usb_uart_bridge_daemon")
    assert manifest
    return manifest



def test_usb_uart_provider_profile_and_identify():
    manifest = _manifest()
    profile = usb_uart_bridge.native_interface_profile()
    assert profile["instrument_family"] == "usb_uart_bridge"
    assert "write_uart" in profile["action_commands"]
    identify = usb_uart_bridge.identify(manifest)
    assert identify["status"] == "ok"
    assert identify["data"]["instrument_family"] == "usb_uart_bridge"



def test_usb_uart_provider_status_and_doctor(monkeypatch):
    manifest = _manifest()
    monkeypatch.setattr(
        "ael.instruments.interfaces.usb_uart_bridge._http_call",
        lambda manifest, path, **kwargs: {"status": "ok", "data": {"ok": True, "selected_serial_number": "ABC123"}},
    )
    status = usb_uart_bridge.get_status(manifest)
    assert status["status"] == "ok"
    assert status["data"]["health_domains"]["bridge_service"]["ok"] is True
    doctor = usb_uart_bridge.doctor(manifest)
    assert doctor["status"] == "ok"
    assert doctor["data"]["checks"]["bridge_service"]["ok"] is True



def test_usb_uart_provider_action_wrappers(monkeypatch):
    manifest = _manifest()
    monkeypatch.setattr(
        "ael.instruments.interfaces.usb_uart_bridge._http_call",
        lambda manifest, path, **kwargs: {"status": "ok", "data": {"path": path, "payload": kwargs.get("payload")}},
    )
    opened = usb_uart_bridge.open_uart(manifest)
    assert opened["status"] == "ok"
    written = usb_uart_bridge.write_uart(manifest, text="ping")
    assert written["data"]["path"] == "/write"
    assert written["data"]["payload"]["text"] == "ping"
    read = usb_uart_bridge.read_uart(manifest, size=64)
    assert read["data"]["payload"]["size"] == 64
