from __future__ import annotations

import base64
import http.client
import json
import threading
from pathlib import Path

import pytest

from ael.instruments import usb_uart_bridge_daemon as bridge


class FakePort:
    def __init__(self, device, serial_number, vid=0x10C4, pid=0xEA60, manufacturer="Vendor", product="UART"):
        self.device = device
        self.serial_number = serial_number
        self.vid = vid
        self.pid = pid
        self.manufacturer = manufacturer
        self.product = product


class FakeSerial:
    def __init__(self, port, baudrate, bytesize, parity, stopbits, timeout):
        self.port = port
        self.settings = {
            "baudrate": baudrate,
            "bytesize": bytesize,
            "parity": parity,
            "stopbits": stopbits,
            "timeout": timeout,
        }
        self.closed = False
        self.buffer = b"hello"

    def close(self):
        self.closed = True

    def write(self, data):
        self.buffer = data
        return len(data)

    def read(self, size):
        return self.buffer[:size]


def _ports(*items):
    return list(items)


def test_discover_lists_only_unique_serial_devices(tmp_path, monkeypatch):
    by_id = tmp_path / "by-id"
    by_id.mkdir()
    (by_id / "usb-bridge").symlink_to("/dev/ttyUSB0")

    monkeypatch.setattr(bridge, "_import_serial", lambda: type("S", (), {"tools": type("T", (), {"list_ports": type("LP", (), {"comports": lambda: []})})}))
    payload = bridge.discover_usb_uart_devices(
        list_ports_fn=lambda: _ports(
            FakePort("/dev/ttyUSB0", "A123"),
            FakePort("/dev/ttyUSB1", ""),
            FakePort("/dev/ttyUSB2", "DUP"),
            FakePort("/dev/ttyUSB3", "DUP"),
        ),
        by_id_dir=by_id,
    )

    assert [entry["serial_number"] for entry in payload["devices"]] == ["A123"]
    assert payload["devices"][0]["by_id_path"] == str(by_id / "usb-bridge")
    rejected_reasons = {entry["reason"] for entry in payload["rejected"]}
    assert "missing_serial_number" in rejected_reasons
    assert "duplicate_serial_number" in rejected_reasons
    assert payload["duplicate_serial_numbers"] == ["DUP"]


def test_config_load_save_round_trip(tmp_path):
    config_path = tmp_path / "bridge.yaml"
    payload = bridge.load_bridge_config(config_path)
    assert payload["usb_uart_bridge"]["selected_serial_number"] is None

    payload["usb_uart_bridge"]["selected_serial_number"] = "ABC123"
    bridge.save_bridge_config(config_path, payload)
    loaded = bridge.load_bridge_config(config_path)
    assert loaded["usb_uart_bridge"]["selected_serial_number"] == "ABC123"


def test_select_bridge_device_saves_serial(tmp_path, monkeypatch):
    config_path = tmp_path / "bridge.yaml"
    monkeypatch.setattr(
        bridge,
        "discover_usb_uart_devices",
        lambda **_: {"ok": True, "devices": [{"serial_number": "ABC123", "device_path": "/dev/ttyUSB0"}], "rejected": [], "duplicate_serial_numbers": []},
    )
    payload = bridge.select_bridge_device(config_path, "ABC123")
    assert payload["usb_uart_bridge"]["selected_serial_number"] == "ABC123"
    resolved = bridge.resolve_selected_device(config_path)
    assert resolved["ok"] is True
    assert resolved["device"]["device_path"] == "/dev/ttyUSB0"


def test_resolve_selected_device_rejects_duplicate_serial(tmp_path):
    config_path = tmp_path / "bridge.yaml"
    payload = bridge.load_bridge_config(config_path)
    payload["usb_uart_bridge"]["selected_serial_number"] = "ABC123"
    bridge.save_bridge_config(config_path, payload)

    resolved = bridge.resolve_selected_device(
        config_path,
        discovery={"ok": True, "devices": [], "rejected": [], "duplicate_serial_numbers": ["ABC123"]},
    )
    assert resolved["ok"] is False
    assert "duplicated" in resolved["error"]


def test_doctor_reports_missing_and_openable(tmp_path):
    config_path = tmp_path / "bridge.yaml"
    payload = bridge.load_bridge_config(config_path)
    payload["usb_uart_bridge"]["selected_serial_number"] = "ABC123"
    bridge.save_bridge_config(config_path, payload)

    missing = bridge.doctor_selected_device(config_path, discovery={"ok": True, "devices": [], "rejected": [], "duplicate_serial_numbers": []})
    assert missing["ok"] is False
    assert missing["present"] is False

    ok = bridge.doctor_selected_device(
        config_path,
        serial_factory=FakeSerial,
        discovery={
            "ok": True,
            "devices": [{"serial_number": "ABC123", "device_path": "/dev/ttyUSB0"}],
            "rejected": [],
            "duplicate_serial_numbers": [],
        },
    )
    assert ok["ok"] is True
    assert ok["present"] is True
    assert ok["openable"] is True
    assert ok["resolved_tty_path"] == "/dev/ttyUSB0"


def test_service_open_write_read_close(tmp_path):
    config_path = tmp_path / "bridge.yaml"
    payload = bridge.load_bridge_config(config_path)
    payload["usb_uart_bridge"]["selected_serial_number"] = "ABC123"
    bridge.save_bridge_config(config_path, payload)

    service = bridge.USBUARTBridgeService(
        config_path,
        serial_factory=FakeSerial,
        list_ports_fn=lambda: _ports(FakePort("/dev/ttyUSB0", "ABC123")),
        by_id_dir=tmp_path / "missing",
    )
    opened = service.open()
    assert opened["ok"] is True

    write = service.write(text="ping")
    assert write["ok"] is True
    assert write["bytes_written"] == 4

    read = service.read(size=8)
    assert read["ok"] is True
    assert base64.b64decode(read["data_b64"]) == b"ping"
    assert read["text"] == "ping"

    closed = service.close()
    assert closed["ok"] is True


def test_http_daemon_endpoints(tmp_path):
    config_path = tmp_path / "bridge.yaml"
    payload = bridge.load_bridge_config(config_path)
    payload["usb_uart_bridge"]["selected_serial_number"] = "ABC123"
    bridge.save_bridge_config(config_path, payload)

    service = bridge.USBUARTBridgeService(
        config_path,
        serial_factory=FakeSerial,
        list_ports_fn=lambda: _ports(FakePort("/dev/ttyUSB0", "ABC123")),
        by_id_dir=tmp_path / "missing",
    )
    try:
        server = bridge._USBUARTBridgeHTTPServer(("127.0.0.1", 0), service)
    except PermissionError:
        pytest.skip("sandbox does not allow loopback sockets")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        conn = http.client.HTTPConnection(host, port, timeout=2)
        conn.request("GET", "/status")
        status = json.loads(conn.getresponse().read().decode("utf-8"))
        assert status["ok"] is True

        conn.request("POST", "/open", body=b"{}")
        opened = json.loads(conn.getresponse().read().decode("utf-8"))
        assert opened["ok"] is True

        body = json.dumps({"text": "bridge"}).encode("utf-8")
        conn.request("POST", "/write", body=body, headers={"Content-Type": "application/json"})
        written = json.loads(conn.getresponse().read().decode("utf-8"))
        assert written["bytes_written"] == 6

        conn.request("POST", "/read", body=json.dumps({"size": 16}).encode("utf-8"), headers={"Content-Type": "application/json"})
        read = json.loads(conn.getresponse().read().decode("utf-8"))
        assert base64.b64decode(read["data_b64"]) == b"bridge"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
