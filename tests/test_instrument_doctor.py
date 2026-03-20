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


def test_doctor_usb_uart_bridge_manifest_reports_provider_health():
    with patch(
        "ael.instrument_doctor.native_api_dispatch.doctor",
        return_value={
            "status": "ok",
            "data": {
                "reachable": True,
                "checks": {
                    "tcp": {"ok": True},
                    "bridge_service": {"ok": True},
                    "uart_surface": {"ok": True},
                },
            },
        },
    ):
        payload = instrument_doctor.doctor(REPO_ROOT, "usb_uart_bridge_daemon")

    assert payload["ok"] is True
    assert payload["kind"] == "instrument"
    assert payload["id"] == "usb_uart_bridge_daemon"
    assert payload["instrument_family"] == "usb_uart_bridge"
    assert payload["native_interface"]["protocol"] == "ael.local_instrument.native_api.v0.1"
    assert payload["native_interface"]["instrument_family"] == "usb_uart_bridge"
    assert payload["checks"]["native_doctor"]["status"] == "ok"
    assert payload["checks"]["bridge_service"]["ok"] is True
    assert payload["resolved_view"]["id"] == "usb_uart_bridge_daemon"
    rendered = instrument_view.render_doctor_text(payload)
    assert "usb_uart_bridge_daemon" in rendered
    assert "bridge_service: ok=True" in rendered
    assert "native_interface:" in rendered



def test_doctor_probe_instance_reports_stlink_native_profile():
    class _Provider:
        family = "stlink"

        @staticmethod
        def native_interface_profile():
            return {
                "protocol": "ael.local_instrument.stlink_native_api.v0.1",
                "instrument_family": "stlink",
                "role": "instrument_native_api",
            }

    class _Binding:
        raw = {
            "probe": {"name": "ST-Link"},
            "connection": {"ip": "127.0.0.1", "gdb_port": 4242},
            "gdb_cmd": "arm-none-eabi-gdb",
        }
        communication = {
            "primary": "gdb_remote",
            "surfaces": [{"name": "gdb_remote", "endpoint": "127.0.0.1:4242"}],
        }
        capability_surfaces = {"swd": "gdb_remote"}
        instance_id = "stlink_stm32f103_gpio"
        type_id = "stlink"
        endpoint_host = "127.0.0.1"
        endpoint_port = 4242
        metadata_validation_errors = []

    with patch(
        "ael.instrument_doctor.load_probe_binding",
        return_value=_Binding(),
    ), patch(
        "ael.instrument_doctor.native_api_dispatch.control_doctor",
        return_value={"status": "ok", "data": {"reachable": True, "checks": {"gdb_remote": {"ok": True}}}},
    ), patch(
        "ael.instrument_doctor.native_api_dispatch.control_get_status",
        return_value={"status": "ok", "data": {"reachable": True}},
    ), patch(
        "ael.instrument_doctor.native_api_dispatch.control_identify",
        return_value={"status": "ok", "data": {"instrument_family": "stlink", "instrument_role": "control"}},
    ), patch(
        "ael.instrument_doctor.native_api_dispatch.control_get_capabilities",
        return_value={"status": "ok", "data": {"capability_families": {"debug_remote": {}}}},
    ), patch(
        "ael.instrument_doctor.resolve_control_provider",
        return_value=_Provider(),
    ):
        payload = instrument_doctor.doctor_probe_instance(REPO_ROOT, "stlink_stm32f103_gpio")

    assert payload["ok"] is True
    assert payload["instrument_family"] == "stlink"
    assert payload["instrument_role"] == "control"
    assert payload["native_interface"]["instrument_family"] == "stlink"
    assert payload["native_interface"]["protocol"] == "ael.local_instrument.stlink_native_api.v0.1"
