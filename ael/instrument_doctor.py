from __future__ import annotations

import socket
from pathlib import Path
from typing import Any, Dict, Optional

from ael.doctor_checks import la_capture_ok, monitor_version
from ael.instrument_metadata import capability_names, validate_capability_surfaces, validate_communication
from ael.instruments.registry import InstrumentRegistry
from ael.instruments import provision as instrument_provision
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
    return cfg


def doctor_probe_instance(repo_root: str | Path, instance_id: str) -> Dict[str, Any]:
    binding = load_probe_binding(repo_root, instance_id=instance_id)
    probe_cfg = _probe_cfg_from_binding(binding)
    tcp = _tcp_check(binding.endpoint_host, binding.endpoint_port)
    monitor_ok, monitor_detail = monitor_version(probe_cfg)
    la_ok, la_detail = la_capture_ok(probe_cfg)
    checks = {
        "tcp": tcp,
        "monitor_version": {"ok": bool(monitor_ok), "detail": monitor_detail},
        "logic_analyzer": {"ok": bool(la_ok), "detail": la_detail},
    }
    overall_ok = bool(tcp.get("ok") and monitor_ok and la_ok)
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
        "kind": "probe_instance",
        "canonical_kind": "control_instrument_instance",
        "id": binding.instance_id,
        "type": binding.type_id,
        "instrument_role": "control",
        "control_instrument": control_instrument,
        "endpoint": {"host": binding.endpoint_host, "port": binding.endpoint_port},
        "communication": dict(binding.communication or {}),
        "capability_surfaces": dict(binding.capability_surfaces or {}),
        "metadata_validation_errors": list(binding.metadata_validation_errors),
        "checks": checks,
    }


def doctor_instrument_manifest(instrument_id: str) -> Dict[str, Any]:
    manifest = InstrumentRegistry().get(instrument_id)
    if not manifest:
        return {"ok": False, "error": f"instrument not found: {instrument_id}"}

    communication = manifest.get("communication", {}) if isinstance(manifest.get("communication"), dict) else {}
    endpoint = communication.get("endpoint")
    host, port = _split_host_port(endpoint)
    checks: Dict[str, Any] = {}

    if instrument_id == "esp32s3_dev_c_meter":
        try:
            checks["reachability"] = instrument_provision.ensure_meter_reachable(manifest=manifest, host=host, timeout_s=1.0)
        except Exception as exc:
            checks["reachability"] = {"ok": False, "error": str(exc), "host": host}
        overall_ok = bool((checks.get("reachability") or {}).get("ok"))
    else:
        if host and port is not None:
            checks["tcp"] = _tcp_check(host, port)
            overall_ok = bool((checks.get("tcp") or {}).get("ok"))
        else:
            checks["availability"] = {"ok": False, "error": "no active doctor available for this instrument type"}
            overall_ok = False

    return {
        "ok": overall_ok,
        "kind": "instrument",
        "id": instrument_id,
        "endpoint": endpoint,
        "communication": dict(communication or {}),
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
    }


def doctor(repo_root: str | Path, target_id: str) -> Dict[str, Any]:
    resolved = build_resolved_instrument_view(Path(repo_root), target_id)
    if not resolved.get("ok"):
        return resolved
    if resolved.get("kind") == "probe_instance":
        payload = doctor_probe_instance(repo_root, target_id)
    else:
        payload = doctor_instrument_manifest(target_id)
    payload["resolved_view"] = resolved
    return payload
