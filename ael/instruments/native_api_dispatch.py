from __future__ import annotations

from typing import Any, Dict

from ael.instruments.interfaces.registry import resolve_control_provider, resolve_manifest_provider

"""
Native dispatch boundary notes:

- dispatch now resolves instrument-family providers instead of hard-coding
  behavior directly in this module
- manifest instruments and control-instrument configs keep separate resolution
  helpers because their source shapes are different today
- outward function names remain stable so callers do not need to change during
  the provider/registry migration
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
    provider = resolve_manifest_provider(manifest)
    if provider is None:
        instrument_id = str(manifest.get("id") or "").strip()
        return _unsupported("native_identify_unsupported", f"native identify unsupported for instrument: {instrument_id}")
    return provider.identify(manifest)



def get_capabilities(manifest: Dict[str, Any]) -> Dict[str, Any]:
    provider = resolve_manifest_provider(manifest)
    if provider is None:
        instrument_id = str(manifest.get("id") or "").strip()
        return _unsupported("native_get_capabilities_unsupported", f"native capabilities unsupported for instrument: {instrument_id}")
    return provider.get_capabilities(manifest)



def doctor(manifest: Dict[str, Any]) -> Dict[str, Any]:
    provider = resolve_manifest_provider(manifest)
    if provider is None:
        instrument_id = str(manifest.get("id") or "").strip()
        return _unsupported("native_doctor_unsupported", f"native doctor unsupported for instrument: {instrument_id}")
    return provider.doctor(manifest)



def get_status(manifest: Dict[str, Any]) -> Dict[str, Any]:
    provider = resolve_manifest_provider(manifest)
    if provider is None:
        instrument_id = str(manifest.get("id") or "").strip()
        return _unsupported("native_status_unsupported", f"native status unsupported for instrument: {instrument_id}")
    return provider.get_status(manifest)



def measure_digital(manifest: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    provider = resolve_manifest_provider(manifest)
    if provider is None:
        instrument_id = str(manifest.get("id") or "").strip()
        return _unsupported("native_measure_digital_unsupported", f"native measure_digital unsupported for instrument: {instrument_id}")
    payload = provider.invoke_action(manifest, "measure_digital", **kwargs)
    if payload.get("status") == "error" and ((payload.get("error") or {}).get("code") == "unsupported_action"):
        instrument_id = str(manifest.get("id") or "").strip()
        return _unsupported("native_measure_digital_unsupported", f"native measure_digital unsupported for instrument: {instrument_id}")
    return payload



def measure_voltage(manifest: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    provider = resolve_manifest_provider(manifest)
    if provider is None:
        instrument_id = str(manifest.get("id") or "").strip()
        return _unsupported("native_measure_voltage_unsupported", f"native measure_voltage unsupported for instrument: {instrument_id}")
    payload = provider.invoke_action(manifest, "measure_voltage", **kwargs)
    if payload.get("status") == "error" and ((payload.get("error") or {}).get("code") == "unsupported_action"):
        instrument_id = str(manifest.get("id") or "").strip()
        return _unsupported("native_measure_voltage_unsupported", f"native measure_voltage unsupported for instrument: {instrument_id}")
    return payload



def stim_digital(manifest: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    provider = resolve_manifest_provider(manifest)
    if provider is None:
        instrument_id = str(manifest.get("id") or "").strip()
        return _unsupported("native_stim_digital_unsupported", f"native stim_digital unsupported for instrument: {instrument_id}")
    payload = provider.invoke_action(manifest, "stim_digital", **kwargs)
    if payload.get("status") == "error" and ((payload.get("error") or {}).get("code") == "unsupported_action"):
        instrument_id = str(manifest.get("id") or "").strip()
        return _unsupported("native_stim_digital_unsupported", f"native stim_digital unsupported for instrument: {instrument_id}")
    return payload



def control_identify(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    provider = resolve_control_provider(probe_cfg)
    if provider is None:
        return _unsupported("control_identify_unsupported", "control identify unsupported for probe config")
    return provider.identify(probe_cfg)



def control_get_capabilities(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    provider = resolve_control_provider(probe_cfg)
    if provider is None:
        return _unsupported("control_get_capabilities_unsupported", "control capabilities unsupported for probe config")
    return provider.get_capabilities(probe_cfg)



def control_get_status(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    provider = resolve_control_provider(probe_cfg)
    if provider is None:
        return _unsupported("control_get_status_unsupported", "control status unsupported for probe config")
    return provider.get_status(probe_cfg)



def control_doctor(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    provider = resolve_control_provider(probe_cfg)
    if provider is None:
        return _unsupported("control_doctor_unsupported", "control doctor unsupported for probe config")
    return provider.doctor(probe_cfg)



def capture_signature(probe_cfg: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    provider = resolve_control_provider(probe_cfg)
    if provider is None:
        return _unsupported("control_capture_signature_unsupported", "capture_signature unsupported for probe config")
    payload = provider.invoke_action(probe_cfg, "capture_signature", **kwargs)
    if payload.get("status") == "error" and ((payload.get("error") or {}).get("code") == "unsupported_action"):
        return _unsupported("control_capture_signature_unsupported", "capture_signature unsupported for probe config")
    return payload



def preflight_probe(probe_cfg: Dict[str, Any]) -> Dict[str, Any]:
    provider = resolve_control_provider(probe_cfg)
    if provider is None:
        return _unsupported("control_preflight_probe_unsupported", "preflight_probe unsupported for probe config")
    payload = provider.invoke_action(probe_cfg, "preflight_probe")
    if payload.get("status") == "error" and ((payload.get("error") or {}).get("code") == "unsupported_action"):
        return _unsupported("control_preflight_probe_unsupported", "preflight_probe unsupported for probe config")
    return payload



def program_firmware(probe_cfg: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    provider = resolve_control_provider(probe_cfg)
    if provider is None:
        return _unsupported("control_program_firmware_unsupported", "program_firmware unsupported for probe config")
    payload = provider.invoke_action(probe_cfg, "program_firmware", **kwargs)
    if payload.get("status") == "error" and ((payload.get("error") or {}).get("code") == "unsupported_action"):
        return _unsupported("control_program_firmware_unsupported", "program_firmware unsupported for probe config")
    return payload
