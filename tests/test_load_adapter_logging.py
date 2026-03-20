from pathlib import Path
from unittest.mock import patch

from ael.adapter_registry import _LoadAdapter


def test_load_gdbmi_does_not_wrap_flash_in_tee(tmp_path):
    adapter = _LoadAdapter("gdbmi")
    ctx = object()
    plan = {"stage_execution": {"requested_until": "run"}}
    step = {
        "inputs": {
            "probe_cfg": {"ip": "192.168.2.98"},
            "firmware_path": str(tmp_path / "fw.elf"),
            "flash_cfg": {"flash_log_path": str(tmp_path / "flash.log")},
            "flash_json_path": str(tmp_path / "flash.json"),
            "output_mode": "normal",
            "log_path": str(tmp_path / "tee.log"),
        }
    }
    Path(step["inputs"]["firmware_path"]).write_text("stub", encoding="utf-8")

    with patch("ael.adapter_registry.flash_bmda_gdbmi.run", return_value=True) as flash_run, patch(
        "ael.adapter_registry._tee_output"
    ) as tee_output:
        result = adapter.execute(step, plan, ctx)

    assert result["ok"] is True
    flash_run.assert_called_once()
    tee_output.assert_not_called()


def test_load_idf_esptool_does_not_crash_when_flash_succeeds(tmp_path):
    adapter = _LoadAdapter("idf_esptool")
    ctx = object()
    plan = {"stage_execution": {"requested_until": "run"}}
    step = {
        "inputs": {
            "probe_cfg": {},
            "firmware_path": str(tmp_path / "fw.elf"),
            "flash_cfg": {"target": "esp32c6"},
            "flash_json_path": str(tmp_path / "flash.json"),
            "output_mode": "normal",
        }
    }
    Path(step["inputs"]["firmware_path"]).write_text("stub", encoding="utf-8")

    with patch("ael.adapter_registry.flash_idf.run", return_value=True) as flash_run:
        result = adapter.execute(step, plan, ctx)

    assert result == {"ok": True}
    flash_run.assert_called_once()


def test_load_idf_esptool_returns_load_failed_when_flash_fails(tmp_path):
    adapter = _LoadAdapter("idf_esptool")
    ctx = object()
    plan = {"stage_execution": {"requested_until": "run"}}
    step = {
        "inputs": {
            "probe_cfg": {},
            "firmware_path": str(tmp_path / "fw.elf"),
            "flash_cfg": {"target": "esp32c6"},
            "flash_json_path": str(tmp_path / "flash.json"),
            "output_mode": "normal",
        }
    }
    Path(step["inputs"]["firmware_path"]).write_text("stub", encoding="utf-8")

    with patch("ael.adapter_registry.flash_idf.run", return_value=False) as flash_run:
        result = adapter.execute(step, plan, ctx)

    assert result["ok"] is False
    assert result["error_summary"] == "load failed"
    flash_run.assert_called_once()
