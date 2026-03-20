from __future__ import annotations

from typing import Any, Dict

from ael.instruments import control_instrument_native_api


def program_firmware(probe_cfg: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    return control_instrument_native_api.program_firmware(probe_cfg, **kwargs)


def capture_signature(probe_cfg: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    return control_instrument_native_api.capture_signature(probe_cfg, **kwargs)
