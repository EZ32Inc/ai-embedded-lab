import json
import os
import subprocess
import sys
from pathlib import Path

from ael import instrument_view


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_build_resolved_probe_instance_view():
    payload = instrument_view.build_resolved_instrument_view(REPO_ROOT, "esp32jtag_stm32_golden")
    assert payload["ok"] is True
    assert payload["kind"] == "control_instrument_instance"
    assert payload["legacy_kind"] == "probe_instance"
    assert payload["id"] == "esp32jtag_stm32_golden"
    assert payload["type"] == "esp32jtag"
    assert payload["instrument_family"] == "esp32jtag"
    assert payload["instrument_role"] == "control"
    assert payload["communication"]["primary"] == "gdb_remote"
    assert payload["capability_surfaces"]["swd"] == "gdb_remote"
    assert payload["native_interface"]["instrument_family"] == "esp32jtag"
    assert payload["native_interface_summary"]["metadata_command_count"] == 4
    assert "stm32f103_gpio" in payload["referenced_by"]["boards"]


def test_build_resolved_instrument_manifest_view():
    payload = instrument_view.build_resolved_instrument_view(REPO_ROOT, "esp32s3_dev_c_meter")
    assert payload["ok"] is True
    assert payload["kind"] == "instrument"
    assert payload["id"] == "esp32s3_dev_c_meter"
    assert payload["communication"]["protocol"] == "gpio_meter_v1"
    assert payload["capability_surfaces"]["measure.digital"] == "primary"
    assert payload["native_interface"]["role"] == "instrument_native_api"
    assert payload["native_interface_summary"]["metadata_command_count"] == 4
    assert payload["native_interface_summary"]["action_command_count"] == 3
    assert "measure_digital" in payload["native_interface"]["action_commands"]
    assert payload["metadata_validation_errors"] == []


def test_build_resolved_usb_uart_bridge_manifest_view():
    payload = instrument_view.build_resolved_instrument_view(REPO_ROOT, "usb_uart_bridge_daemon")
    assert payload["ok"] is True
    assert payload["kind"] == "instrument"
    assert payload["id"] == "usb_uart_bridge_daemon"
    assert payload["communication"]["protocol"] == "ael-usb-uart-bridge-v0.1"
    assert payload["native_interface"]["protocol"] == "ael.local_instrument.native_api.v0.1"
    assert payload["capability_surfaces"]["observe.uart"] == "primary"
    assert payload["capability_surfaces"]["bridge.serial"] == "primary"
    assert payload["metadata_validation_errors"] == []


def test_instruments_describe_cli_text_output():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [sys.executable, "-m", "ael", "instruments", "describe", "--id", "esp32jtag_stm32_golden", "--format", "text"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "id: esp32jtag_stm32_golden" in res.stdout
    assert "kind: control_instrument_instance" in res.stdout
    assert "legacy_kind: probe_instance" in res.stdout
    assert "surfaces:" in res.stdout
    assert "gdb_remote" in res.stdout
    assert "web_api" in res.stdout
    assert "instrument_family: esp32jtag" in res.stdout
    assert "native_interface:" in res.stdout
    assert "capability_surfaces:" in res.stdout
    assert "referenced_by:" in res.stdout


def test_instruments_describe_cli_json_output():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [sys.executable, "-m", "ael", "instruments", "describe", "--id", "esp32s3_dev_c_meter", "--format", "json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    payload = json.loads(res.stdout)
    assert payload["ok"] is True
    assert payload["kind"] == "instrument"
    assert payload["id"] == "esp32s3_dev_c_meter"


def test_instruments_describe_cli_summary_output():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [sys.executable, "-m", "ael", "instruments", "describe", "--id", "esp32s3_dev_c_meter", "--format", "summary"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "esp32s3_dev_c_meter [instrument]" in res.stdout
    assert "endpoint: 192.168.4.1:9000" in res.stdout
    assert "capability_surfaces:" in res.stdout
    assert "native_actions: measure_digital, measure_voltage, stim_digital" in res.stdout
    assert "native_metadata_count: 4" in res.stdout
    assert "native_action_count: 3" in res.stdout


def test_instruments_describe_cli_text_output_shows_native_interface():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(
        [sys.executable, "-m", "ael", "instruments", "describe", "--id", "usb_uart_bridge_daemon", "--format", "text"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "native_interface:" in res.stdout
    assert "ael.local_instrument.native_api.v0.1" in res.stdout
