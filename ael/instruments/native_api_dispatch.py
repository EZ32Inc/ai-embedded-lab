from __future__ import annotations

from typing import Any, Dict

from ael.instruments import control_instrument_native_api
from ael.instruments import jtag_native_api
from ael.instruments import meter_native_api

"""
Native dispatch boundary notes:

- control-instrument operations stay on control_instrument_native_api
- ESP32 meter metadata and doctor/status stay on meter_native_api
- ESP32 meter action execution also enters through meter_native_api, which now
  bridges those actions onto the unified esp32_meter backend
"""


def _unsupported(code: str, message: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "retryable": False,
        },
    }


def identify(manifest: Dict[str, Any]) -> Dict[str, Any]:
    instrument_id = str(manifest.get("id") or "").strip()
    if instrument_id == "esp32s3_dev_c_meter":
        return meter_native_api.identify(manifest)
    return _unsupported("native_identify_unsupported", f"native identify unsupported for instrument: {instrument_id}")


def get_capabilities(manifest: Dict[str, Any]) -> Dict[str, Any]:
    instrument_id = str(manifest.get("id") or "").strip()
    if instrument_id == "esp32s3_dev_c_meter":
        return meter_native_api.get_capabilities(manifest)
    return _unsupported("native_get_capabilities_unsupported", f"native capabilities unsupported for instrument: {instrument_id}")


def doctor(manifest: Dict[str, Any]) -> Dict[str, Any]:
    instrument_id = str(manifest.get("id") or "").strip()
    if instrument_id == "esp32s3_dev_c_meter":
        return meter_native_api.doctor(manifest)
    return _unsupported("native_doctor_unsupported", f"native doctor unsupported for instrument: {instrument_id}")


def get_status(manifest: Dict[str, Any]) -> Dict[str, Any]:
    instrument_id = str(manifest.get("id") or "").strip()
    if instrument_id == "esp32s3_dev_c_meter":
        return meter_native_api.get_status(manifest)
    return _unsupported("native_status_unsupported", f"native status unsupported for instrument: {instrument_id}")


def measure_digital(manifest: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    instrument_id = str(manifest.get("id") or "").strip()
    if instrument_id == "esp32s3_dev_c_meter":
        return meter_native_api.measure_digital(manifest, **kwargs)
    return _unsupported("native_measure_digital_unsupported", f"native measure_digital unsupported for instrument: {instrument_id}")


def measure_voltage(manifest: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    instrument_id = str(manifest.get("id") or "").strip()
    if instrument_id == "esp32s3_dev_c_meter":
        return meter_native_api.measure_voltage(manifest, **kwargs)
    return _unsupported("native_measure_voltage_unsupported", f"native measure_voltage unsupported for instrument: {instrument_id}")


def stim_digital(manifest: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    instrument_id = str(manifest.get("id") or "").strip()
    if instrument_id == "esp32s3_dev_c_meter":
        return meter_native_api.stim_digital(manifest, **kwargs)
    return _unsupported("native_stim_digital_unsupported", f"native stim_digital unsupported for instrument: {instrument_id}")


def control_identify(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    return jtag_native_api.identify(probe_cfg)


def control_get_capabilities(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    return jtag_native_api.get_capabilities(probe_cfg)


def control_get_status(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    return jtag_native_api.get_status(probe_cfg)


def control_doctor(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    return jtag_native_api.doctor(probe_cfg)


def capture_signature(probe_cfg: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    return control_instrument_native_api.capture_signature(probe_cfg, **kwargs)


def preflight_probe(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    return control_instrument_native_api.preflight_probe(probe_cfg)


def program_firmware(probe_cfg: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    return control_instrument_native_api.program_firmware(probe_cfg, **kwargs)
