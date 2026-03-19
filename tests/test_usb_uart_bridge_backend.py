from __future__ import annotations

import sys
import types

from ael.instruments.backends.usb_uart_bridge.backend import UsbUartBridgeBackend, invoke


class _FakeSerial:
    def __init__(self, port, baudrate, timeout):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._lines = [b"hello\n", b"world\n"]

    def readline(self):
        return self._lines.pop(0) if self._lines else b""

    def close(self):
        return None


def _install_fake_serial(monkeypatch):
    fake_module = types.SimpleNamespace(Serial=_FakeSerial)
    monkeypatch.setitem(sys.modules, "serial", fake_module)


def _instrument():
    return {
        "name": "uart_bridge_1",
        "driver": "usb_uart_bridge",
        "connection": {"serial_port": "/dev/ttyUSB0", "baud": 115200},
        "config": {"read_timeout_s": 0.1},
    }


def test_usb_uart_backend_reads_uart(monkeypatch):
    _install_fake_serial(monkeypatch)
    out = UsbUartBridgeBackend("/dev/ttyUSB0", 115200, 0.1).execute("uart_read", {"duration_s": 0.0})
    assert out["status"] == "success"
    assert out["action"] == "uart_read"


def test_usb_uart_invoke_wait_for(monkeypatch):
    _install_fake_serial(monkeypatch)
    out = invoke("uart_wait_for", _instrument(), {"pattern": "world", "timeout_s": 0.01}, {"dut": "dut1"})
    assert out["ok"] is True
    assert out["action"] == "uart_wait_for"
