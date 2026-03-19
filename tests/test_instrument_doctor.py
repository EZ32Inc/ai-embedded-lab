from pathlib import Path
from unittest.mock import patch

from ael import instrument_doctor
from ael import instrument_view


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_doctor_probe_instance_reports_probe_health():
    with patch(
        "ael.instrument_doctor.native_api_dispatch.control_doctor",
        return_value={"status": "ok", "data": {"reachable": True, "checks": {"debug_remote": {"ok": True}, "capture_control": {"ok": True}, "preflight": {"ok": True, "detail": "ok"}}}},
    ), patch(
        "ael.instrument_doctor.native_api_dispatch.control_get_status",
        return_value={"status": "ok", "data": {"reachable": True}},
    ), patch(
        "ael.instrument_doctor.native_api_dispatch.control_identify",
        return_value={"status": "ok", "data": {"instrument_family": "esp32jtag"}},
    ), patch(
        "ael.instrument_doctor.native_api_dispatch.control_get_capabilities",
        return_value={"status": "ok", "data": {"capability_families": {"debug_remote": {}, "capture_control": {}}}},
    ):
        payload = instrument_doctor.doctor(REPO_ROOT, "esp32jtag_stm32_golden")

    assert payload["ok"] is True
    assert payload["kind"] == "control_instrument_instance"
    assert payload["legacy_kind"] == "probe_instance"
    assert payload["id"] == "esp32jtag_stm32_golden"
    assert payload["instrument_family"] == "esp32jtag"
    assert payload["instrument_role"] == "control"
    assert payload["control_instrument"]["kind"] == "control_instrument_instance"
    assert payload["control_instrument"]["legacy_kind"] == "probe_instance"
    assert payload["native_interface"]["instrument_family"] == "esp32jtag"
    assert payload["checks"]["gdb_remote"]["ok"] is True
    assert payload["checks"]["capture_subsystem"]["ok"] is True
    assert payload["capability_surfaces"]["swd"] == "gdb_remote"
    assert payload["resolved_view"]["id"] == "esp32jtag_stm32_golden"
    assert payload["resolved_view"]["kind"] == "control_instrument_instance"
    assert payload["resolved_view"]["legacy_kind"] == "probe_instance"
    rendered = instrument_view.render_doctor_text(payload)
    assert "resolved_instrument:" in rendered
    assert "checks:" in rendered
    assert "instrument_family: esp32jtag" in rendered
    assert "gdb_remote: ok=True" in rendered


def test_doctor_meter_manifest_reports_reachability():
    with patch(
        "ael.instrument_doctor.native_api_dispatch.doctor",
        return_value={
            "status": "ok",
            "data": {
                "reachable": True,
                "checks": {
                    "network": {"ok": True},
                    "reachability": {"ok": True, "host": "192.168.4.1", "tcp_port": 9000},
                    "measurement_surface": {"ok": True},
                },
            },
        },
    ):
        payload = instrument_doctor.doctor(REPO_ROOT, "esp32s3_dev_c_meter")

    assert payload["ok"] is True
    assert payload["kind"] == "instrument"
    assert payload["id"] == "esp32s3_dev_c_meter"
    assert payload["instrument_family"] == "esp32_meter"
    assert payload["checks"]["native_doctor"]["status"] == "ok"
    assert payload["native_interface"]["role"] == "instrument_native_api"
    assert payload["checks"]["reachability"]["ok"] is True
    assert payload["capability_surfaces"]["measure.digital"] == "primary"
    assert payload["resolved_view"]["id"] == "esp32s3_dev_c_meter"
    assert payload["resolved_view"]["kind"] == "instrument"
    rendered = instrument_view.render_doctor_text(payload)
    assert "esp32s3_dev_c_meter" in rendered
    assert "instrument_family: esp32_meter" in rendered
    assert "native_doctor: ok=None" in rendered
    assert "reachability: ok=True" in rendered
    assert "action_commands: measure_digital, measure_voltage, stim_digital" in rendered


def test_doctor_usb_uart_bridge_manifest_reports_tcp_health():
    with patch(
        "ael.instrument_doctor._tcp_check",
        return_value={"ok": True, "host": "127.0.0.1", "port": 8767},
    ):
        payload = instrument_doctor.doctor(REPO_ROOT, "usb_uart_bridge_daemon")

    assert payload["ok"] is True
    assert payload["kind"] == "instrument"
    assert payload["id"] == "usb_uart_bridge_daemon"
    assert payload["native_interface"]["protocol"] == "ael.local_instrument.native_api.v0.1"
    assert payload["checks"]["tcp"]["ok"] is True
    assert payload["resolved_view"]["id"] == "usb_uart_bridge_daemon"
    rendered = instrument_view.render_doctor_text(payload)
    assert "usb_uart_bridge_daemon" in rendered
    assert "tcp: ok=True" in rendered
    assert "native_interface:" in rendered
