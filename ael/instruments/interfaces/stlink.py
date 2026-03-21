from __future__ import annotations

from ael.instruments import stlink_native_api
from ael.instruments.interfaces.base import InstrumentProvider
from ael.instruments.interfaces.model import (
    normalize_capabilities_result,
    normalize_doctor_result,
    normalize_status_result,
    wrap_legacy_action,
)


STLINK_CAPABILITIES = {
    "probe.preflight": {"actions": ["preflight_probe"], "surfaces": ["instrument_native_api"]},
    "debug.attach": {"actions": ["preflight_probe"], "surfaces": ["gdb_remote"]},
    "debug.flash": {"actions": ["program_firmware"], "surfaces": ["gdb_remote"]},
    "debug.reset": {"actions": ["reset"], "surfaces": ["gdb_remote"]},
    "debug.halt": {"actions": ["debug_halt"], "surfaces": ["gdb_remote"]},
    "debug.memory_read": {"actions": ["debug_read_memory"], "surfaces": ["gdb_remote"]},
}


STATUS_FALLBACK = {
    "strategy": "restart_local_probe_services",
    "suggestion": "confirm the local ST-Link GDB endpoint is up before scheduling flash or attach work",
}


DOCTOR_FALLBACK = {
    "strategy": "recover_probe_then_retry",
    "suggestion": "check probe USB health and restart the managed ST-Link GDB server before retrying",
}


PROGRAM_FIRMWARE_FALLBACK = {
    "strategy": "retry_after_probe_recovery",
    "suggestion": "retry after confirming ST-Link probe health or restarting the managed local GDB server",
}


PREFLIGHT_FALLBACK = {
    "strategy": "retry_after_probe_recovery",
    "suggestion": "confirm the local ST-Link GDB endpoint is reachable before scheduling probe work",
}



def _capability_map(probe_cfg):
    capability_surfaces = probe_cfg.get("capability_surfaces") if isinstance(probe_cfg.get("capability_surfaces"), dict) else {}
    transport = str(capability_surfaces.get("swd") or "gdb_remote")
    mapping = {key: {**value} for key, value in STLINK_CAPABILITIES.items()}
    for key in ("debug.attach", "debug.flash", "debug.reset", "debug.halt", "debug.memory_read"):
        mapping[key]["surfaces"] = [transport]
    return mapping



def _get_capabilities(probe_cfg):
    payload = stlink_native_api.get_capabilities(probe_cfg)
    return wrap_legacy_action(
        payload,
        family="stlink",
        action="get_capabilities",
        success_mapper=lambda _data: normalize_capabilities_result(
            family="stlink",
            capabilities=_capability_map(probe_cfg),
            lifecycle_boundary=stlink_native_api.native_interface_profile().get("lifecycle_scope"),
        ),
        failure_boundary="instrument_capabilities",
    )



def _get_status(probe_cfg):
    payload = stlink_native_api.get_status(probe_cfg)
    return wrap_legacy_action(
        payload,
        family="stlink",
        action="get_status",
        success_mapper=lambda data: normalize_status_result(
            family="stlink",
            reachable=data.get("reachable"),
            health_domains=(data.get("health_domains") or {}) if isinstance(data.get("health_domains"), dict) else {},
            endpoints=(data.get("endpoints") or {}) if isinstance(data.get("endpoints"), dict) else {},
        ),
        failure_boundary="instrument_status",
        fallback=STATUS_FALLBACK,
    )



def _doctor(probe_cfg):
    payload = stlink_native_api.doctor(probe_cfg)
    return wrap_legacy_action(
        payload,
        family="stlink",
        action="doctor",
        success_mapper=lambda data: normalize_doctor_result(
            family="stlink",
            reachable=data.get("reachable"),
            checks=(data.get("checks") or {}) if isinstance(data.get("checks"), dict) else {},
            lifecycle_boundary=data.get("lifecycle_boundary") if isinstance(data.get("lifecycle_boundary"), dict) else None,
            recovery_hint="check probe USB health and restart the managed ST-Link GDB server before retrying",
            failure_boundary="probe_health",
        ),
        failure_boundary="probe_health",
        fallback=DOCTOR_FALLBACK,
    )



def _preflight_probe(probe_cfg):
    payload = stlink_native_api.preflight_probe(probe_cfg)
    return wrap_legacy_action(
        payload,
        family="stlink",
        action="preflight_probe",
        success_mapper=lambda data: {
            "transport": "gdb_remote",
            "gdb_remote": (data.get("preflight") or {}).get("gdb_remote"),
            "preflight": data.get("preflight") if isinstance(data.get("preflight"), dict) else {},
        },
        failure_boundary="probe_health",
        fallback=PREFLIGHT_FALLBACK,
    )



def _program_firmware(probe_cfg, **kwargs):
    requested = {
        "firmware_path": kwargs.get("firmware_path"),
        "transport": "gdb_remote",
    }
    payload = stlink_native_api.program_firmware(probe_cfg, **kwargs)
    return wrap_legacy_action(
        payload,
        family="stlink",
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


PROVIDER = InstrumentProvider(
    family="stlink",
    native_interface_profile=stlink_native_api.native_interface_profile,
    identify=stlink_native_api.identify,
    get_capabilities=_get_capabilities,
    get_status=_get_status,
    doctor=_doctor,
    actions={
        "preflight_probe": _preflight_probe,
        "program_firmware": _program_firmware,
    },
)
