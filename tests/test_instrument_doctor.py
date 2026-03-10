from pathlib import Path
from unittest.mock import patch

from ael import instrument_doctor


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_doctor_probe_instance_reports_probe_health():
    with patch("ael.instrument_doctor.monitor_version", return_value=(True, "bmda ok")), patch(
        "ael.instrument_doctor.la_capture_ok",
        return_value=(True, "len=65532"),
    ), patch(
        "ael.instrument_doctor._tcp_check",
        return_value={"ok": True, "host": "192.168.2.98", "port": 4242},
    ):
        payload = instrument_doctor.doctor(REPO_ROOT, "esp32jtag_stm32_golden")

    assert payload["ok"] is True
    assert payload["kind"] == "probe_instance"
    assert payload["id"] == "esp32jtag_stm32_golden"
    assert payload["checks"]["monitor_version"]["ok"] is True
    assert payload["checks"]["logic_analyzer"]["ok"] is True
    assert payload["capability_surfaces"]["swd"] == "gdb_remote"
    assert payload["resolved_view"]["id"] == "esp32jtag_stm32_golden"
    assert payload["resolved_view"]["kind"] == "probe_instance"


def test_doctor_meter_manifest_reports_reachability():
    with patch(
        "ael.instrument_doctor.instrument_provision.ensure_meter_reachable",
        return_value={"ok": True, "host": "192.168.4.1", "tcp_port": 9000},
    ):
        payload = instrument_doctor.doctor(REPO_ROOT, "esp32s3_dev_c_meter")

    assert payload["ok"] is True
    assert payload["kind"] == "instrument"
    assert payload["id"] == "esp32s3_dev_c_meter"
    assert payload["checks"]["reachability"]["ok"] is True
    assert payload["capability_surfaces"]["measure.digital"] == "primary"
    assert payload["resolved_view"]["id"] == "esp32s3_dev_c_meter"
    assert payload["resolved_view"]["kind"] == "instrument"
