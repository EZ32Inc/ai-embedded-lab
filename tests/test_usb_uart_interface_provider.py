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
    assert status["data"]["status_model_version"] == "instrument_status/v1"
    assert status["data"]["health"] == "ready"
    assert status["data"]["health_domains"]["bridge_service"]["ok"] is True
    doctor = usb_uart_bridge.doctor(manifest)
    assert doctor["status"] == "ok"
    assert doctor["data"]["doctor_model_version"] == "instrument_doctor/v1"
    assert doctor["data"]["health"] == "healthy"
    assert doctor["data"]["checks"]["bridge_service"]["ok"] is True



def test_usb_uart_provider_action_wrappers(monkeypatch):
    manifest = _manifest()
    monkeypatch.setattr(
        "ael.instruments.interfaces.usb_uart_bridge._http_call",
        lambda manifest, path, **kwargs: {"status": "ok", "data": {"path": path, "payload": kwargs.get("payload")}},
    )
    opened = usb_uart_bridge.PROVIDER.invoke_action(manifest, "open")
    assert opened["status"] == "ok"
    assert opened["family"] == "usb_uart_bridge"
    assert opened["action"] == "open"
    assert opened["data"]["session_state"] == "open"
    written = usb_uart_bridge.PROVIDER.invoke_action(manifest, "write_uart", text="ping")
    assert written["status"] == "ok"
    assert written["family"] == "usb_uart_bridge"
    assert written["action"] == "write_uart"
    assert written["data"]["path"] == "/write"
    assert written["data"]["payload"]["text"] == "ping"
    read = usb_uart_bridge.PROVIDER.invoke_action(manifest, "read_uart", size=64)
    assert read["status"] == "ok"
    assert read["family"] == "usb_uart_bridge"
    assert read["action"] == "read_uart"
    assert read["data"]["payload"]["size"] == 64
    closed = usb_uart_bridge.PROVIDER.invoke_action(manifest, "close")
    assert closed["status"] == "ok"
    assert closed["data"]["session_state"] == "closed"
