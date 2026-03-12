from __future__ import annotations

from typing import Any, Dict

from ael.instruments import meter_native_api


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
