from __future__ import annotations

import json

from ael import usb_uart_bridge_cli as cli


def test_cli_list_json(monkeypatch, capsys):
    monkeypatch.setattr(
        "ael.instruments.usb_uart_bridge_daemon.discover_usb_uart_devices",
        lambda **_: {
            "ok": True,
            "devices": [{"serial_number": "ABC123", "device_path": "/dev/ttyUSB0", "vid": 0x10C4, "pid": 0xEA60}],
            "rejected": [],
            "duplicate_serial_numbers": [],
        },
    )
    rc = cli.main(["list"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["devices"][0]["serial_number"] == "ABC123"


def test_cli_select_show_doctor(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "bridge.yaml"
    monkeypatch.setattr(
        "ael.instruments.usb_uart_bridge_daemon.discover_usb_uart_devices",
        lambda **_: {
            "ok": True,
            "devices": [{"serial_number": "ABC123", "device_path": "/dev/ttyUSB0"}],
            "rejected": [],
            "duplicate_serial_numbers": [],
        },
    )

    rc = cli.main(["--config", str(config_path), "select", "--serial", "ABC123"])
    assert rc == 0
    selected = json.loads(capsys.readouterr().out)
    assert selected["selected_serial_number"] == "ABC123"

    rc = cli.main(["--config", str(config_path), "show"])
    assert rc == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["device"]["device_path"] == "/dev/ttyUSB0"

    monkeypatch.setattr(
        "ael.instruments.usb_uart_bridge_daemon.doctor_selected_device",
        lambda config_path: {
            "ok": True,
            "selected_serial_number": "ABC123",
            "present": True,
            "openable": True,
            "resolved_tty_path": "/dev/ttyUSB0",
        },
    )
    rc = cli.main(["--config", str(config_path), "doctor"])
    assert rc == 0
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["openable"] is True


def test_cli_show_failure(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "bridge.yaml"
    monkeypatch.setattr(
        "ael.instruments.usb_uart_bridge_daemon.resolve_selected_device",
        lambda config_path: {"ok": False, "error": "not configured"},
    )
    rc = cli.main(["--config", str(config_path), "show"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "not configured"

