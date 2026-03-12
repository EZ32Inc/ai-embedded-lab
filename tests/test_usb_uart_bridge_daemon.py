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
    by_path = tmp_path / "by-path"
    by_path.mkdir()
    (by_id / "usb-bridge").symlink_to("/dev/ttyUSB0")
    (by_path / "pci-bridge").symlink_to("/dev/ttyUSB2")

    monkeypatch.setattr(bridge, "_import_serial", lambda: type("S", (), {"tools": type("T", (), {"list_ports": type("LP", (), {"comports": lambda: []})})}))
    payload = bridge.discover_usb_uart_devices(
        list_ports_fn=lambda: _ports(
            FakePort("/dev/ttyUSB0", "A123"),
            FakePort("/dev/ttyUSB1", ""),
            FakePort("/dev/ttyUSB2", "0"),
            FakePort("/dev/ttyUSB3", "DUP"),
            FakePort("/dev/ttyUSB4", "DUP"),
        ),
        by_id_dir=by_id,
        by_path_dir=by_path,
    )

    assert [entry["identity_value"] for entry in payload["devices"]] == ["A123", str(by_path / "pci-bridge")]
    assert payload["devices"][0]["by_id_path"] == str(by_id / "usb-bridge")
    assert payload["devices"][1]["identity_kind"] == "usb_path"
    assert payload["devices"][1]["serial_number"] is None
    rejected_reasons = {entry["reason"] for entry in payload["rejected"]}
    assert "missing_stable_identity" in rejected_reasons
    assert "duplicate_stable_identity" in rejected_reasons
    assert payload["duplicate_device_identities"] == [{"kind": "usb_serial", "value": "DUP"}]


def test_config_load_save_round_trip(tmp_path):
    config_path = tmp_path / "bridge.yaml"
    payload = bridge.load_bridge_config(config_path)
    assert payload["usb_uart_bridge"]["selected_serial_number"] is None
    assert payload["usb_uart_bridge"]["selected_identity_kind"] is None
    assert payload["usb_uart_bridge"]["selected_identity_value"] is None

    payload["usb_uart_bridge"]["selected_identity_kind"] = "usb_serial"
    payload["usb_uart_bridge"]["selected_identity_value"] = "ABC123"
    payload["usb_uart_bridge"]["selected_serial_number"] = "ABC123"
    bridge.save_bridge_config(config_path, payload)
    loaded = bridge.load_bridge_config(config_path)
    assert loaded["usb_uart_bridge"]["selected_serial_number"] == "ABC123"
    assert loaded["usb_uart_bridge"]["selected_identity_kind"] == "usb_serial"


def test_select_bridge_device_saves_serial(tmp_path, monkeypatch):
    config_path = tmp_path / "bridge.yaml"
    monkeypatch.setattr(
        bridge,
        "discover_usb_uart_devices",
        lambda **_: {"ok": True, "devices": [{"identity_kind": "usb_serial", "identity_value": "ABC123", "serial_number": "ABC123", "device_path": "/dev/ttyUSB0"}], "rejected": [], "duplicate_device_identities": []},
    )
    payload = bridge.select_bridge_device(config_path, "ABC123")
    assert payload["usb_uart_bridge"]["selected_serial_number"] == "ABC123"
    assert payload["usb_uart_bridge"]["selected_identity_kind"] == "usb_serial"
    assert payload["usb_uart_bridge"]["selected_identity_value"] == "ABC123"
    resolved = bridge.resolve_selected_device(config_path)
    assert resolved["ok"] is True
    assert resolved["device"]["device_path"] == "/dev/ttyUSB0"


def test_select_bridge_device_updates_serial_settings(tmp_path, monkeypatch):
    config_path = tmp_path / "bridge.yaml"
    monkeypatch.setattr(
        bridge,
        "discover_usb_uart_devices",
        lambda **_: {
            "ok": True,
            "devices": [{
                "identity_kind": "usb_serial",
                "identity_value": "ABC123",
                "serial_number": "ABC123",
                "device_path": "/dev/ttyUSB0",
            }],
            "rejected": [],
            "duplicate_device_identities": [],
        },
    )
    payload = bridge.select_bridge_device(
        config_path,
        "ABC123",
        serial_settings={
            "baudrate": 9600,
            "bytesize": 7,
            "parity": "E",
            "stopbits": 2,
            "timeout": 0.5,
        },
    )
    serial_cfg = payload["usb_uart_bridge"]["serial"]
    assert serial_cfg["baudrate"] == 9600
    assert serial_cfg["bytesize"] == 7
    assert serial_cfg["parity"] == "E"
    assert serial_cfg["stopbits"] == 2
    assert serial_cfg["timeout"] == 0.5


def test_select_bridge_device_accepts_non_serial_identity(tmp_path, monkeypatch):
    config_path = tmp_path / "bridge.yaml"
    monkeypatch.setattr(
        bridge,
        "discover_usb_uart_devices",
        lambda **_: {
            "ok": True,
            "devices": [{
                "identity_kind": "usb_path",
                "identity_value": "/dev/serial/by-path/pci-0000:00:14.0-usb-0:14.4:1.0-port0",
                "serial_number": None,
                "device_path": "/dev/ttyUSB0",
            }],
            "rejected": [],
            "duplicate_device_identities": [],
        },
    )
    payload = bridge.select_bridge_device(
        config_path,
        identity_value="/dev/serial/by-path/pci-0000:00:14.0-usb-0:14.4:1.0-port0",
    )
    assert payload["usb_uart_bridge"]["selected_identity_kind"] == "usb_path"
    assert payload["usb_uart_bridge"]["selected_serial_number"] is None


def test_resolve_selected_device_rejects_duplicate_identity(tmp_path):
    config_path = tmp_path / "bridge.yaml"
    payload = bridge.load_bridge_config(config_path)
    payload["usb_uart_bridge"]["selected_identity_kind"] = "usb_serial"
    payload["usb_uart_bridge"]["selected_identity_value"] = "ABC123"
    payload["usb_uart_bridge"]["selected_serial_number"] = "ABC123"
    bridge.save_bridge_config(config_path, payload)

    resolved = bridge.resolve_selected_device(
        config_path,
        discovery={"ok": True, "devices": [], "rejected": [], "duplicate_device_identities": [{"kind": "usb_serial", "value": "ABC123"}]},
    )
    assert resolved["ok"] is False
    assert "duplicated" in resolved["error"]


def test_doctor_reports_missing_and_openable(tmp_path):
    config_path = tmp_path / "bridge.yaml"
    payload = bridge.load_bridge_config(config_path)
    payload["usb_uart_bridge"]["selected_identity_kind"] = "usb_serial"
    payload["usb_uart_bridge"]["selected_identity_value"] = "ABC123"
    payload["usb_uart_bridge"]["selected_serial_number"] = "ABC123"
    bridge.save_bridge_config(config_path, payload)

    missing = bridge.doctor_selected_device(config_path, discovery={"ok": True, "devices": [], "rejected": [], "duplicate_device_identities": []})
    assert missing["ok"] is False
    assert missing["present"] is False

    ok = bridge.doctor_selected_device(
        config_path,
        serial_factory=FakeSerial,
        discovery={
            "ok": True,
            "devices": [{"identity_kind": "usb_serial", "identity_value": "ABC123", "serial_number": "ABC123", "device_path": "/dev/ttyUSB0"}],
            "rejected": [],
            "duplicate_device_identities": [],
        },
    )
    assert ok["ok"] is True
    assert ok["present"] is True
    assert ok["openable"] is True
    assert ok["resolved_tty_path"] == "/dev/ttyUSB0"
    assert ok["selected_identity_kind"] == "usb_serial"


def test_service_open_write_read_close(tmp_path):
    config_path = tmp_path / "bridge.yaml"
    payload = bridge.load_bridge_config(config_path)
    payload["usb_uart_bridge"]["selected_identity_kind"] = "usb_serial"
    payload["usb_uart_bridge"]["selected_identity_value"] = "ABC123"
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


def test_native_interface_metadata_commands(tmp_path):
    config_path = tmp_path / "bridge.yaml"
    payload = bridge.load_bridge_config(config_path)
    payload["usb_uart_bridge"]["selected_identity_kind"] = "usb_serial"
    payload["usb_uart_bridge"]["selected_identity_value"] = "ABC123"
    payload["usb_uart_bridge"]["selected_serial_number"] = "ABC123"
    bridge.save_bridge_config(config_path, payload)

    service = bridge.USBUARTBridgeService(
        config_path,
        serial_factory=FakeSerial,
        list_ports_fn=lambda: _ports(FakePort("/dev/ttyUSB0", "ABC123")),
        by_id_dir=tmp_path / "missing",
    )

    identify = service.identify()
    assert identify["status"] == "ok"
    assert identify["data"]["protocol_version"] == bridge.NATIVE_API_PROTOCOL

    caps = service.get_capabilities()
    assert caps["status"] == "ok"
    assert "observe.uart" in caps["data"]["capabilities"]

    status = service.get_status()
    assert status["status"] == "ok"
    assert status["data"]["selected_serial_number"] == "ABC123"


def test_native_interface_doctor_error_shape(tmp_path):
    service = bridge.USBUARTBridgeService(tmp_path / "bridge.yaml")
    payload = service.doctor()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "doctor_failed"


def test_http_daemon_endpoints(tmp_path):
    config_path = tmp_path / "bridge.yaml"
    payload = bridge.load_bridge_config(config_path)
    payload["usb_uart_bridge"]["selected_identity_kind"] = "usb_serial"
    payload["usb_uart_bridge"]["selected_identity_value"] = "ABC123"
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

        conn.request("GET", "/identify")
        identify = json.loads(conn.getresponse().read().decode("utf-8"))
        assert identify["status"] == "ok"

        conn.request("GET", "/get_capabilities")
        caps = json.loads(conn.getresponse().read().decode("utf-8"))
        assert caps["status"] == "ok"

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
