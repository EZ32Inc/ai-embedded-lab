from __future__ import annotations

from ael.instruments import jtag_native_api
from ael.instruments.interfaces.base import InstrumentProvider
from ael.instruments.interfaces.model import (
    normalize_capabilities_result,
    normalize_doctor_result,
    normalize_status_result,
    wrap_legacy_action,
)


JTAG_CAPABILITIES = {
    "probe.preflight": {"actions": ["preflight_probe"], "surfaces": ["instrument_native_api"]},
    "debug.flash": {"actions": ["program_firmware"], "surfaces": ["gdb_remote"]},
    "debug.reset": {"actions": ["reset"], "surfaces": ["reset_out"]},
    "debug.halt": {"actions": ["debug_halt"], "surfaces": ["gdb_remote"]},
    "debug.memory_read": {"actions": ["debug_read_memory"], "surfaces": ["gdb_remote"]},
    "capture.digital": {"actions": ["capture_signature"], "surfaces": ["web_api"]},
}


STATUS_FALLBACK = {
    "strategy": "refresh_probe_status",
    "suggestion": "re-check ESP32 JTAG connectivity and rerun preflight before using the setup",
}


DOCTOR_FALLBACK = {
    "strategy": "rerun_preflight_then_retry",
    "suggestion": "rerun ESP32 JTAG preflight and inspect monitor targets plus logic-analyzer self-test before retrying",
}


PROGRAM_FIRMWARE_FALLBACK = {
    "strategy": "retry_same_setup",
    "suggestion": "retry firmware programming on the same ESP32 JTAG setup after re-running preflight",
}


CAPTURE_SIGNATURE_FALLBACK = {
    "strategy": "rerun_capture_after_preflight",
    "suggestion": "rerun preflight and verify capture wiring before retrying signature capture on the ESP32 JTAG setup",
}



def _capability_map(probe_cfg):
    capability_surfaces = probe_cfg.get("capability_surfaces", {}) if isinstance(probe_cfg.get("capability_surfaces"), dict) else {}
    mapping = {key: {**value} for key, value in JTAG_CAPABILITIES.items()}
    mapping["debug.flash"]["surfaces"] = [str(capability_surfaces.get("swd") or "gdb_remote")]
    mapping["debug.halt"]["surfaces"] = [str(capability_surfaces.get("swd") or "gdb_remote")]
    mapping["debug.memory_read"]["surfaces"] = [str(capability_surfaces.get("swd") or "gdb_remote")]
    mapping["debug.reset"]["surfaces"] = [str(capability_surfaces.get("reset_out") or "reset_out")]
    mapping["capture.digital"]["surfaces"] = [str(capability_surfaces.get("gpio_in") or "web_api")]
    return mapping



def _get_capabilities(probe_cfg):
    payload = jtag_native_api.get_capabilities(probe_cfg)
    return wrap_legacy_action(
        payload,
        family="esp32jtag",
        action="get_capabilities",
        success_mapper=lambda _data: normalize_capabilities_result(
            family="esp32jtag",
            capabilities=_capability_map(probe_cfg),
            lifecycle_boundary=jtag_native_api.native_interface_profile().get("lifecycle_scope"),
        ),
        failure_boundary="instrument_capabilities",
    )



def _get_status(probe_cfg):
    payload = jtag_native_api.get_status(probe_cfg)
    return wrap_legacy_action(
        payload,
        family="esp32jtag",
        action="get_status",
        success_mapper=lambda data: normalize_status_result(
            family="esp32jtag",
            reachable=data.get("reachable"),
            health_domains=(data.get("health_domains") or {}) if isinstance(data.get("health_domains"), dict) else {},
            endpoints=(data.get("endpoints") or {}) if isinstance(data.get("endpoints"), dict) else {},
        ),
        failure_boundary="instrument_status",
        fallback=STATUS_FALLBACK,
    )



def _doctor(probe_cfg):
    payload = jtag_native_api.doctor(probe_cfg)
    return wrap_legacy_action(
        payload,
        family="esp32jtag",
        action="doctor",
        success_mapper=lambda data: normalize_doctor_result(
            family="esp32jtag",
            reachable=data.get("reachable"),
            checks=(data.get("checks") or {}) if isinstance(data.get("checks"), dict) else {},
            lifecycle_boundary=data.get("lifecycle_boundary") if isinstance(data.get("lifecycle_boundary"), dict) else None,
            recovery_hint="rerun preflight and inspect monitor targets plus logic-analyzer self-test",
            failure_boundary="probe_health",
        ),
        failure_boundary="probe_health",
        fallback=DOCTOR_FALLBACK,
    )



def _program_firmware(probe_cfg, **kwargs):
    requested = {
        "firmware_path": kwargs.get("firmware_path"),
        "transport": "gdb_remote",
    }
    payload = jtag_native_api.program_firmware(probe_cfg, **kwargs)
    return wrap_legacy_action(
        payload,
        family="esp32jtag",
        action="program_firmware",
        requested=requested,
        success_mapper=lambda data: {
            "firmware_path": data.get("firmware_path"),
            "transport": "gdb_remote",
            "managed_debug_server": data.get("managed_stlink_server"),
        },
        failure_boundary="firmware_programming",
        fallback=PROGRAM_FIRMWARE_FALLBACK,
    )



def _capture_signature(probe_cfg, **kwargs):
    requested = {
        "pin": kwargs.get("pin"),
        "pins": list(kwargs.get("pins") or []),
        "duration_s": kwargs.get("duration_s"),
        "expected_hz": kwargs.get("expected_hz"),
        "min_edges": kwargs.get("min_edges"),
        "max_edges": kwargs.get("max_edges"),
    }
    payload = jtag_native_api.capture_signature(probe_cfg, **kwargs)
    return wrap_legacy_action(
        payload,
        family="esp32jtag",
        action="capture_signature",
        requested=requested,
        success_mapper=lambda data: {
            "pin": data.get("pin") or kwargs.get("pin"),
            "pins": list(kwargs.get("pins") or ([data.get("pin")] if data.get("pin") else [kwargs.get("pin")]) or []),
            "duration_s": kwargs.get("duration_s"),
            "expected_hz": kwargs.get("expected_hz"),
            "edge_count": data.get("edges"),
            "high_count": data.get("high"),
            "low_count": data.get("low"),
            "capture_blob_present": data.get("blob") is not None,
            "blob": data.get("blob"),
            "edges": data.get("edges"),
            "high": data.get("high"),
            "low": data.get("low"),
            "sample_rate_hz": data.get("sample_rate_hz"),
            "bit": data.get("bit"),
            "pin_bits": data.get("pin_bits") if isinstance(data.get("pin_bits"), dict) else {},
        },
        failure_boundary="signal_capture",
        fallback=CAPTURE_SIGNATURE_FALLBACK,
    )


PROVIDER = InstrumentProvider(
    family="esp32jtag",
    native_interface_profile=jtag_native_api.native_interface_profile,
    identify=jtag_native_api.identify,
    get_capabilities=_get_capabilities,
    get_status=_get_status,
    doctor=_doctor,
    actions={
        "preflight_probe": jtag_native_api.preflight_probe,
        "program_firmware": _program_firmware,
        "capture_signature": _capture_signature,
    },
)
