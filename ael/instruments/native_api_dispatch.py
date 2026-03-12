from __future__ import annotations

from typing import Any, Dict

from ael.instruments import meter_native_api


def doctor(manifest: Dict[str, Any]) -> Dict[str, Any]:
    instrument_id = str(manifest.get("id") or "").strip()
    if instrument_id == "esp32s3_dev_c_meter":
        return meter_native_api.doctor(manifest)
    return {
        "status": "error",
        "error": {
            "code": "native_doctor_unsupported",
            "message": f"native doctor unsupported for instrument: {instrument_id}",
            "retryable": False,
        },
    }


def get_status(manifest: Dict[str, Any]) -> Dict[str, Any]:
    instrument_id = str(manifest.get("id") or "").strip()
    if instrument_id == "esp32s3_dev_c_meter":
        return meter_native_api.get_status(manifest)
    return {
        "status": "error",
        "error": {
            "code": "native_status_unsupported",
            "message": f"native status unsupported for instrument: {instrument_id}",
            "retryable": False,
        },
    }
