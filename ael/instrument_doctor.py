from __future__ import annotations

import socket
from pathlib import Path
from typing import Any, Dict, Optional

from ael.instrument_metadata import capability_names, validate_capability_surfaces, validate_communication
from ael.instruments.registry import InstrumentRegistry
from ael.instruments import native_api_dispatch
from ael.instruments.interfaces.model import derive_doctor_health
from ael.instruments.interfaces.registry import control_family, control_native_interface, resolve_control_provider, resolve_manifest_provider
from ael.instrument_view import build_resolved_instrument_view
from ael.probe_binding import load_probe_binding


def _split_host_port(endpoint: str | None) -> tuple[Optional[str], Optional[int]]:
    text = str(endpoint or "").strip()
    if not text:
        return None, None
    if "://" in text:
        scheme, rest = text.split("://", 1)
        _ = scheme
        text = rest
    host_port = text.split("/", 1)[0].strip()
    if ":" not in host_port:
        return host_port or None, None
    host, port = host_port.rsplit(":", 1)
    try:
        return host.strip() or None, int(port.strip())
    except Exception:
        return host.strip() or None, None


def _tcp_check(host: str | None, port: int | None, timeout_s: float = 1.0) -> Dict[str, Any]:
    if not host or port is None:
        return {"ok": False, "error": "missing host/port"}
    try:
        with socket.create_connection((host, int(port)), timeout=timeout_s):
            return {"ok": True, "host": host, "port": int(port)}
    except Exception as exc:
        return {"ok": False, "host": host, "port": int(port), "error": str(exc)}


def _probe_cfg_from_binding(binding) -> Dict[str, Any]:
    probe = binding.raw.get("probe", {}) if isinstance(binding.raw.get("probe"), dict) else {}
    connection = binding.raw.get("connection", {}) if isinstance(binding.raw.get("connection"), dict) else {}
    cfg = dict(probe)
    if "ip" not in cfg and connection.get("ip"):
        cfg["ip"] = connection.get("ip")
    if "gdb_port" not in cfg and connection.get("gdb_port") is not None:
        cfg["gdb_port"] = connection.get("gdb_port")
    if "gdb_cmd" not in cfg and binding.raw.get("gdb_cmd"):
        cfg["gdb_cmd"] = binding.raw.get("gdb_cmd")
    cfg["communication"] = dict(binding.communication or {})
    cfg["capability_surfaces"] = dict(binding.capability_surfaces or {})
    cfg["instance_id"] = binding.instance_id
    cfg["type_id"] = binding.type_id
    return cfg


def doctor_probe_instance(repo_root: str | Path, instance_id: str) -> Dict[str, Any]:
    binding = load_probe_binding(repo_root, instance_id=instance_id)
    probe_cfg = _probe_cfg_from_binding(binding)
    native_doctor = native_api_dispatch.control_doctor(probe_cfg)
    native_status = native_api_dispatch.control_get_status(probe_cfg)
    native_identify = native_api_dispatch.control_identify(probe_cfg)
    native_capabilities = native_api_dispatch.control_get_capabilities(probe_cfg)
    doctor_data = (native_doctor.get("result") or native_doctor.get("data") or {}) if isinstance(native_doctor, dict) else {}
    status_data = (native_status.get("result") or native_status.get("data") or {}) if isinstance(native_status, dict) else {}
    capabilities_data = (native_capabilities.get("result") or native_capabilities.get("data") or {}) if isinstance(native_capabilities, dict) else {}
    checks = {}
    if native_doctor.get("status") == "ok":
        checks = (doctor_data.get("checks") or {}) if isinstance(doctor_data, dict) else {}
        if "gdb_remote" not in checks and "debug_remote" in checks:
            checks["gdb_remote"] = checks.get("debug_remote")
        if "capture_subsystem" not in checks and "capture_control" in checks:
            checks["capture_subsystem"] = checks.get("capture_control")
        overall_ok = bool(doctor_data.get("reachable"))
    else:
        checks["native_doctor"] = {
            "ok": False,
            "error": ((native_doctor.get("error") or {}).get("message") or "native doctor failed"),
        }
        overall_ok = False
    provider = resolve_control_provider(probe_cfg)
    profile = control_native_interface(probe_cfg)
    identify_data = (native_identify.get("data") or {}) if isinstance(native_identify.get("data"), dict) else {}
    control_instrument = {
        "kind": "control_instrument_instance",
        "legacy_kind": "probe_instance",
        "instance": binding.instance_id,
        "type": binding.type_id,
        "endpoint": {"host": binding.endpoint_host, "port": binding.endpoint_port},
        "communication": dict(binding.communication or {}),
        "capability_surfaces": dict(binding.capability_surfaces or {}),
    }
    return {
        "ok": overall_ok,
        "kind": "control_instrument_instance",
        "legacy_kind": "probe_instance",
        "id": binding.instance_id,
        "type": binding.type_id,
        "instrument_family": str(identify_data.get("instrument_family") or (control_family(probe_cfg) or binding.type_id)),
        "instrument_role": str(identify_data.get("instrument_role") or "control"),
        "instrument_interface": profile,
        "native_interface": profile,
        "native_identify": native_identify,
        "native_status": native_status,
        "native_capabilities": native_capabilities,
        "control_instrument": control_instrument,
        "endpoint": {"host": binding.endpoint_host, "port": binding.endpoint_port},
        "communication": dict(binding.communication or {}),
        "capability_surfaces": dict(binding.capability_surfaces or {}),
        "metadata_validation_errors": list(binding.metadata_validation_errors),
        "checks": checks,
        "capability_taxonomy_version": capabilities_data.get("capability_taxonomy_version") if isinstance(capabilities_data, dict) else None,
        "capability_taxonomy_enforced": capabilities_data.get("capability_taxonomy_enforced") if isinstance(capabilities_data, dict) else None,
        "status_model_version": status_data.get("status_model_version") if isinstance(status_data, dict) else None,
        "status_health_schema_version": status_data.get("status_health_schema_version") if isinstance(status_data, dict) else None,
        "status_taxonomy_enforced": status_data.get("status_taxonomy_enforced") if isinstance(status_data, dict) else None,
        "doctor_model_version": doctor_data.get("doctor_model_version") if isinstance(doctor_data, dict) else None,
        "doctor_check_schema_version": doctor_data.get("doctor_check_schema_version") if isinstance(doctor_data, dict) else None,
        "doctor_checks_enforced": doctor_data.get("doctor_checks_enforced") if isinstance(doctor_data, dict) else None,
        "health": (doctor_data.get("health") if isinstance(doctor_data, dict) and doctor_data.get("health") else derive_doctor_health(reachable=bool(overall_ok), checks=checks)),
        "recovery_hint": doctor_data.get("recovery_hint") if isinstance(doctor_data, dict) else None,
        "failure_boundary": doctor_data.get("failure_boundary") if isinstance(doctor_data, dict) else None,
    }


def doctor_instrument_manifest(instrument_id: str) -> Dict[str, Any]:
    manifest = InstrumentRegistry().get(instrument_id)
    if not manifest:
        return {"ok": False, "error": f"instrument not found: {instrument_id}"}

    communication = manifest.get("communication", {}) if isinstance(manifest.get("communication"), dict) else {}
    endpoint = communication.get("endpoint")
    provider = resolve_manifest_provider(manifest)
    checks: Dict[str, Any] = {}
    doctor_data: Dict[str, Any] = {}
    status_data: Dict[str, Any] = {}
    capabilities_data: Dict[str, Any] = {}

    if provider is not None:
        native_status = native_api_dispatch.get_status(manifest)
        native_capabilities = native_api_dispatch.get_capabilities(manifest)
        native_doctor = native_api_dispatch.doctor(manifest)
        status_data = native_status.get("result", {}) if isinstance(native_status.get("result"), dict) else (native_status.get("data", {}) if isinstance(native_status.get("data"), dict) else {})
        capabilities_data = native_capabilities.get("result", {}) if isinstance(native_capabilities.get("result"), dict) else (native_capabilities.get("data", {}) if isinstance(native_capabilities.get("data"), dict) else {})
        checks["native_doctor"] = native_doctor
        doctor_data = native_doctor.get("result", {}) if isinstance(native_doctor.get("result"), dict) else (native_doctor.get("data", {}) if isinstance(native_doctor.get("data"), dict) else {})
        if native_doctor.get("status") == "ok":
            doctor_checks = doctor_data.get("checks") if isinstance(doctor_data.get("checks"), dict) else {}
            checks.update(doctor_checks)
            overall_ok = bool(doctor_data.get("reachable", True))
        else:
            checks["availability"] = {
                "ok": False,
                "error": ((native_doctor.get("error") or {}).get("message") or "native doctor failed"),
            }
            overall_ok = False
    else:
        host, port = _split_host_port(endpoint)
        if host and port is not None:
            checks["tcp"] = _tcp_check(host, port)
            overall_ok = bool((checks.get("tcp") or {}).get("ok"))
        else:
            checks["availability"] = {"ok": False, "error": "no active doctor available for this instrument type"}
            overall_ok = False

    native_interface = provider.native_interface_profile() if provider is not None else dict(manifest.get("native_interface") or {})
    return {
        "ok": overall_ok,
        "kind": "instrument",
        "id": instrument_id,
        "instrument_family": (provider.family if provider is not None else (str((manifest.get("native_interface") or {}).get("instrument_family") or "").strip() or None)),
        "endpoint": endpoint,
        "communication": dict(communication or {}),
        "instrument_interface": native_interface,
        "native_interface": native_interface,
        "capability_surfaces": dict(manifest.get("capability_surfaces") or {}),
        "metadata_validation_errors": (
            validate_communication(communication)
            + validate_capability_surfaces(
                manifest.get("capability_surfaces"),
                capabilities=capability_names(manifest),
                communication=communication,
            )
        ),
        "checks": checks,
        "capability_taxonomy_version": capabilities_data.get("capability_taxonomy_version") if isinstance(capabilities_data, dict) else None,
        "capability_taxonomy_enforced": capabilities_data.get("capability_taxonomy_enforced") if isinstance(capabilities_data, dict) else None,
        "status_model_version": status_data.get("status_model_version") if isinstance(status_data, dict) else None,
        "status_health_schema_version": status_data.get("status_health_schema_version") if isinstance(status_data, dict) else None,
        "status_taxonomy_enforced": status_data.get("status_taxonomy_enforced") if isinstance(status_data, dict) else None,
        "doctor_model_version": doctor_data.get("doctor_model_version") if isinstance(doctor_data, dict) else None,
        "doctor_check_schema_version": doctor_data.get("doctor_check_schema_version") if isinstance(doctor_data, dict) else None,
        "doctor_checks_enforced": doctor_data.get("doctor_checks_enforced") if isinstance(doctor_data, dict) else None,
        "health": (doctor_data.get("health") if isinstance(doctor_data, dict) and doctor_data.get("health") else derive_doctor_health(reachable=bool(overall_ok), checks=checks)),
        "recovery_hint": doctor_data.get("recovery_hint") if isinstance(doctor_data, dict) else None,
        "failure_boundary": doctor_data.get("failure_boundary") if isinstance(doctor_data, dict) else None,
    }


def doctor(repo_root: str | Path, target_id: str) -> Dict[str, Any]:
    resolved = build_resolved_instrument_view(Path(repo_root), target_id)
    if not resolved.get("ok"):
        return resolved
    if resolved.get("kind") == "control_instrument_instance" or resolved.get("legacy_kind") == "probe_instance":
        payload = doctor_probe_instance(repo_root, target_id)
    else:
        payload = doctor_instrument_manifest(target_id)
    payload["resolved_view"] = resolved
    return payload
