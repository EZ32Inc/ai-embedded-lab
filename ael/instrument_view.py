from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ael.instrument_metadata import capability_names, validate_capability_surfaces, validate_communication
from ael.instruments.registry import InstrumentRegistry
from ael.pipeline import _simple_yaml_load
from ael.probe_binding import load_probe_binding


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, Any]:
    import json

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_board_cfg(repo_root: Path, board_id: str) -> Dict[str, Any]:
    path = repo_root / "configs" / "boards" / f"{board_id}.yaml"
    if not path.exists():
        return {}
    raw = _simple_yaml_load(str(path))
    board = raw.get("board", {}) if isinstance(raw, dict) else {}
    return board if isinstance(board, dict) else {}


def _board_reference_index(root: Path) -> tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    probe_refs: Dict[str, List[str]] = {}
    instrument_refs: Dict[str, List[str]] = {}
    boards_dir = root / "configs" / "boards"
    if not boards_dir.exists():
        return probe_refs, instrument_refs
    for path in sorted(boards_dir.glob("*.yaml")):
        board_cfg = _load_board_cfg(root, path.stem)
        board_id = path.stem
        instance_id = str(board_cfg.get("instrument_instance") or "").strip()
        if instance_id:
            probe_refs.setdefault(instance_id, []).append(board_id)
        instrument_cfg = board_cfg.get("instrument", {}) if isinstance(board_cfg.get("instrument"), dict) else {}
        instrument_id = str(instrument_cfg.get("id") or "").strip()
        if instrument_id:
            instrument_refs.setdefault(instrument_id, []).append(board_id)
    return probe_refs, instrument_refs


def _plan_reference_index(root: Path) -> Dict[str, List[str]]:
    refs: Dict[str, List[str]] = {}
    plans_dir = root / "tests" / "plans"
    if not plans_dir.exists():
        return refs
    for path in sorted(plans_dir.glob("*.json")):
        payload = _load_json(path)
        instrument_cfg = payload.get("instrument", {}) if isinstance(payload.get("instrument"), dict) else {}
        instrument_id = str(instrument_cfg.get("id") or "").strip()
        if instrument_id:
            refs.setdefault(instrument_id, []).append(path.relative_to(root).as_posix())
    return refs


def _relpath(root: Path, value: str | None) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    try:
        return path.relative_to(root).as_posix()
    except Exception:
        return text


def build_probe_instance_view(
    repo_root: Path | str | None,
    instance_id: str,
    *,
    referenced_by: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    root = Path(repo_root or REPO_ROOT)
    binding = load_probe_binding(root, instance_id=instance_id)
    refs = referenced_by or {}
    return {
        "kind": "control_instrument_instance",
        "legacy_kind": "probe_instance",
        "id": binding.instance_id,
        "type": binding.type_id,
        "instrument_role": "control",
        "config_path": _relpath(root, binding.config_path),
        "instance_path": _relpath(root, binding.instance_path),
        "type_path": _relpath(root, binding.type_path),
        "endpoint": {
            "host": binding.endpoint_host,
            "port": binding.endpoint_port,
        }
        if (binding.endpoint_host or binding.endpoint_port is not None)
        else None,
        "communication": dict(binding.communication or {}),
        "capability_surfaces": dict(binding.capability_surfaces or {}),
        "metadata_validation_errors": list(binding.metadata_validation_errors),
        "legacy_warning": binding.legacy_warning,
        "referenced_by": {
            "boards": sorted(refs.get("boards", [])),
        },
    }


def build_instrument_manifest_view(
    repo_root: Path | str | None,
    instrument_id: str,
    *,
    referenced_by: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    root = Path(repo_root or REPO_ROOT)
    manifest = InstrumentRegistry().get(instrument_id)
    if not manifest:
        return {"ok": False, "error": f"instrument not found: {instrument_id}"}
    refs = referenced_by or {}
    communication = dict(manifest.get("communication") or {})
    native_interface = dict(manifest.get("native_interface") or {})
    capability_surfaces = dict(manifest.get("capability_surfaces") or {})
    native_interface_summary = {}
    if native_interface:
        native_interface_summary = {
            "protocol": native_interface.get("protocol"),
            "role": native_interface.get("role"),
            "metadata_command_count": len(native_interface.get("metadata_commands") or []),
            "action_command_count": len(native_interface.get("action_commands") or []),
        }
    return {
        "kind": "instrument",
        "id": instrument_id,
        "origin": manifest.get("_origin"),
        "manifest_path": _relpath(root, str(manifest.get("_path") or "")),
        "communication": communication,
        "native_interface": native_interface,
        "native_interface_summary": native_interface_summary,
        "capability_surfaces": capability_surfaces,
        "metadata_validation_errors": (
            validate_communication(communication)
            + validate_capability_surfaces(
                capability_surfaces,
                capabilities=capability_names(manifest),
                communication=communication,
            )
        ),
        "referenced_by": {
            "boards": sorted(refs.get("boards", [])),
            "plans": sorted(refs.get("plans", [])),
        },
    }


def build_resolved_instrument_view(repo_root: Path | str | None, target_id: str) -> Dict[str, Any]:
    root = Path(repo_root or REPO_ROOT)
    instance_path = root / "configs" / "instrument_instances" / f"{target_id}.yaml"
    probe_refs, instrument_refs = _board_reference_index(root)
    plan_refs = _plan_reference_index(root)
    if instance_path.exists():
        payload = build_probe_instance_view(
            root,
            target_id,
            referenced_by={"boards": probe_refs.get(target_id, [])},
        )
        payload["ok"] = True
        return payload
    manifest = InstrumentRegistry().get(target_id)
    if manifest:
        payload = build_instrument_manifest_view(
            root,
            target_id,
            referenced_by={
                "boards": instrument_refs.get(target_id, []),
                "plans": plan_refs.get(target_id, []),
            },
        )
        payload["ok"] = True
        return payload
    return {"ok": False, "error": f"instrument not found: {target_id}"}


def build_resolved_instrument_inventory(repo_root: Path | str | None = None) -> Dict[str, Any]:
    root = Path(repo_root or REPO_ROOT)
    probe_board_refs, instrument_board_refs = _board_reference_index(root)
    instrument_plan_refs = _plan_reference_index(root)

    probe_instances: List[Dict[str, Any]] = []
    instances_dir = root / "configs" / "instrument_instances"
    if instances_dir.exists():
        for path in sorted(instances_dir.glob("*.yaml")):
            probe_instances.append(
                build_probe_instance_view(
                    root,
                    path.stem,
                    referenced_by={"boards": probe_board_refs.get(path.stem, [])},
                )
            )

    instruments: List[Dict[str, Any]] = []
    registry = InstrumentRegistry()
    for manifest in registry.list():
        instrument_id = str(manifest.get("id") or "").strip()
        instruments.append(
            build_instrument_manifest_view(
                root,
                instrument_id,
                referenced_by={
                    "boards": instrument_board_refs.get(instrument_id, []),
                    "plans": instrument_plan_refs.get(instrument_id, []),
                },
            )
        )

    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(root),
        "summary": {
            "control_instrument_instance_count": len(probe_instances),
            "instrument_count": len(instruments),
        },
        "control_instrument_instances": probe_instances,
        "compatibility": {
            "probe_instances": probe_instances,
            "probe_instance_count": len(probe_instances),
        },
        "instruments": instruments,
    }


def render_resolved_instrument_text(payload: Dict[str, Any]) -> str:
    if not payload.get("ok"):
        return f"error: {payload.get('error')}\n"
    lines: List[str] = []
    lines.append(f"id: {payload.get('id')}")
    kind = payload.get("kind")
    lines.append(f"kind: {kind}")
    if payload.get("legacy_kind"):
        lines.append(f"legacy_kind: {payload.get('legacy_kind')}")
    if payload.get("type"):
        lines.append(f"type: {payload.get('type')}")
    if payload.get("instrument_role"):
        lines.append(f"instrument_role: {payload.get('instrument_role')}")
    if payload.get("origin"):
        lines.append(f"origin: {payload.get('origin')}")
    if payload.get("config_path"):
        lines.append(f"config_path: {payload.get('config_path')}")
    if payload.get("instance_path"):
        lines.append(f"instance_path: {payload.get('instance_path')}")
    if payload.get("type_path"):
        lines.append(f"type_path: {payload.get('type_path')}")
    if payload.get("manifest_path"):
        lines.append(f"manifest_path: {payload.get('manifest_path')}")
    endpoint = payload.get("endpoint")
    if isinstance(endpoint, dict) and (endpoint.get("host") or endpoint.get("port") is not None):
        lines.append(f"endpoint: {endpoint.get('host')}:{endpoint.get('port')}")
    if payload.get("legacy_warning"):
        lines.append(f"legacy_warning: {payload.get('legacy_warning')}")
    communication = payload.get("communication")
    if isinstance(communication, dict) and communication:
        lines.append("communication:")
        lines.extend(_render_communication_text(communication, indent="  "))
    native_interface = payload.get("native_interface")
    if isinstance(native_interface, dict) and native_interface:
        lines.append("native_interface:")
        if native_interface.get("name"):
            lines.append(f"  - name: {native_interface.get('name')}")
        if native_interface.get("protocol"):
            lines.append(f"  - protocol: {native_interface.get('protocol')}")
        if native_interface.get("role"):
            lines.append(f"  - role: {native_interface.get('role')}")
        metadata_commands = native_interface.get("metadata_commands") or []
        if metadata_commands:
            lines.append(f"  - metadata_commands: {', '.join(str(item) for item in metadata_commands)}")
        action_commands = native_interface.get("action_commands") or []
        if action_commands:
            lines.append(f"  - action_commands: {', '.join(str(item) for item in action_commands)}")
        response_model = native_interface.get("response_model")
        if response_model is not None:
            lines.append(f"  - response_model: {response_model}")
        for key, value in native_interface.items():
            if key in {"name", "protocol", "role", "metadata_commands", "action_commands", "response_model"}:
                continue
            lines.append(f"  - {key}: {value}")
    native_interface_summary = payload.get("native_interface_summary")
    if isinstance(native_interface_summary, dict) and native_interface_summary:
        lines.append("native_interface_summary:")
        for key, value in native_interface_summary.items():
            lines.append(f"  - {key}: {value}")
    capability_surfaces = payload.get("capability_surfaces")
    if isinstance(capability_surfaces, dict) and capability_surfaces:
        lines.append("capability_surfaces:")
        for key, value in capability_surfaces.items():
            lines.append(f"  - {key}: {value}")
    refs = payload.get("referenced_by")
    if isinstance(refs, dict) and refs:
        lines.append("referenced_by:")
        boards = refs.get("boards") or []
        plans = refs.get("plans") or []
        if boards:
            lines.append(f"  - boards: {', '.join(boards)}")
        if plans:
            lines.append(f"  - plans: {', '.join(plans)}")
    metadata_errors = payload.get("metadata_validation_errors") or []
    if metadata_errors:
        lines.append("metadata_validation_errors:")
        for item in metadata_errors:
            lines.append(f"  - {item}")
    return "\n".join(lines).rstrip() + "\n"


def render_resolved_instrument_summary_text(payload: Dict[str, Any]) -> str:
    if not payload.get("ok"):
        return f"error: {payload.get('error')}\n"
    lines: List[str] = []
    kind = payload.get("kind")
    lines.append(f"{payload.get('id')} [{kind}]")
    if payload.get("legacy_kind"):
        lines.append(f"legacy_kind: {payload.get('legacy_kind')}")
    if payload.get("type"):
        lines.append(f"type: {payload.get('type')}")
    if payload.get("instrument_role"):
        lines.append(f"instrument_role: {payload.get('instrument_role')}")
    if payload.get("origin"):
        lines.append(f"origin: {payload.get('origin')}")
    endpoint = payload.get("endpoint")
    if isinstance(endpoint, dict) and (endpoint.get("host") or endpoint.get("port") is not None):
        lines.append(f"endpoint: {endpoint.get('host')}:{endpoint.get('port')}")
    communication = payload.get("communication") or {}
    if isinstance(communication, dict):
        if not endpoint and communication.get("endpoint"):
            lines.append(f"endpoint: {communication.get('endpoint')}")
        primary = communication.get("primary")
        if primary:
            lines.append(f"primary_surface: {primary}")
        elif communication.get("protocol"):
            lines.append(f"protocol: {communication.get('protocol')}")
    native_interface = payload.get("native_interface") or {}
    if isinstance(native_interface, dict) and native_interface.get("protocol"):
        lines.append(f"native_interface: {native_interface.get('protocol')}")
        metadata_commands = native_interface.get("metadata_commands") or []
        if metadata_commands:
            lines.append(f"native_metadata: {', '.join(str(item) for item in metadata_commands)}")
        action_commands = native_interface.get("action_commands") or []
        if action_commands:
            lines.append(f"native_actions: {', '.join(str(item) for item in action_commands)}")
    native_interface_summary = payload.get("native_interface_summary") or {}
    if isinstance(native_interface_summary, dict) and native_interface_summary:
        if native_interface_summary.get("role"):
            lines.append(f"native_role: {native_interface_summary.get('role')}")
        if native_interface_summary.get("metadata_command_count") is not None:
            lines.append(f"native_metadata_count: {native_interface_summary.get('metadata_command_count')}")
        if native_interface_summary.get("action_command_count") is not None:
            lines.append(f"native_action_count: {native_interface_summary.get('action_command_count')}")
    capability_surfaces = payload.get("capability_surfaces") or {}
    if isinstance(capability_surfaces, dict) and capability_surfaces:
        parts = [f"{key}->{value}" for key, value in capability_surfaces.items()]
        lines.append(f"capability_surfaces: {', '.join(parts)}")
    refs = payload.get("referenced_by") or {}
    if isinstance(refs, dict):
        boards = refs.get("boards") or []
        plans = refs.get("plans") or []
        if boards:
            lines.append(f"used_by_boards: {', '.join(boards)}")
        if plans:
            lines.append(f"used_by_plans: {', '.join(plans)}")
    return "\n".join(lines).rstrip() + "\n"


def render_resolved_instrument_inventory_text(payload: Dict[str, Any]) -> str:
    if not payload.get("ok"):
        return f"error: {payload.get('error')}\n"
    lines: List[str] = []
    summary = payload.get("summary") or {}
    lines.append("Instrument instances")
    lines.append(f"control_instrument_instance_count: {summary.get('control_instrument_instance_count', 0)}")
    lines.append(f"instrument_count: {summary.get('instrument_count', 0)}")
    compat = payload.get("compatibility") or {}
    if compat.get("probe_instance_count") is not None:
        lines.append(f"legacy_probe_instance_count: {compat.get('probe_instance_count')}")
    lines.append("")
    for item in payload.get("control_instrument_instances") or []:
        lines.append(f"{item.get('id')} ({item.get('type')})")
        endpoint = item.get("endpoint")
        if isinstance(endpoint, dict) and (endpoint.get("host") or endpoint.get("port") is not None):
            lines.append(f"  endpoint: {endpoint.get('host')}:{endpoint.get('port')}")
        refs = (item.get("referenced_by") or {}).get("boards") or []
        if refs:
            lines.append(f"  boards: {', '.join(refs)}")
        if item.get("metadata_validation_errors"):
            lines.append(f"  metadata_errors: {len(item.get('metadata_validation_errors') or [])}")
    if payload.get("control_instrument_instances"):
        lines.append("")
    for item in payload.get("instruments") or []:
        lines.append(f"{item.get('id')} ({item.get('origin')})")
        refs = item.get("referenced_by") or {}
        boards = refs.get("boards") or []
        plans = refs.get("plans") or []
        if boards:
            lines.append(f"  boards: {', '.join(boards)}")
        if plans:
            lines.append(f"  plans: {', '.join(plans)}")
        if item.get("metadata_validation_errors"):
            lines.append(f"  metadata_errors: {len(item.get('metadata_validation_errors') or [])}")
    return "\n".join(lines).rstrip() + "\n"


def render_doctor_text(payload: Dict[str, Any]) -> str:
    if not payload.get("ok") and not payload.get("resolved_view"):
        return f"error: {payload.get('error')}\n"
    lines: List[str] = []
    resolved = payload.get("resolved_view")
    if isinstance(resolved, dict) and resolved:
        lines.append("resolved_instrument:")
        for line in render_resolved_instrument_text(resolved).rstrip().splitlines():
            lines.append(f"  {line}")
    if "ok" in payload:
        lines.append(f"doctor_ok: {payload.get('ok')}")
    native_interface = payload.get("native_interface")
    if isinstance(native_interface, dict) and native_interface:
        lines.append("native_interface:")
        if native_interface.get("name"):
            lines.append(f"  name: {native_interface.get('name')}")
        if native_interface.get("protocol"):
            lines.append(f"  protocol: {native_interface.get('protocol')}")
        if native_interface.get("role"):
            lines.append(f"  role: {native_interface.get('role')}")
        metadata_commands = native_interface.get("metadata_commands") or []
        if metadata_commands:
            lines.append(f"  metadata_commands: {', '.join(str(item) for item in metadata_commands)}")
        action_commands = native_interface.get("action_commands") or []
        if action_commands:
            lines.append(f"  action_commands: {', '.join(str(item) for item in action_commands)}")
        if native_interface.get("response_model") is not None:
            lines.append(f"  response_model: {native_interface.get('response_model')}")
        for key, value in native_interface.items():
            if key in {"name", "protocol", "role", "metadata_commands", "action_commands", "response_model"}:
                continue
            lines.append(f"  {key}: {value}")
    checks = payload.get("checks") or {}
    if isinstance(checks, dict) and checks:
        lines.append("checks:")
        for name, detail in checks.items():
            if isinstance(detail, dict):
                status = detail.get("ok")
                lines.append(f"  - {name}: ok={status}")
                for key, value in detail.items():
                    if key == "ok":
                        continue
                    lines.append(f"    {key}: {value}")
            else:
                lines.append(f"  - {name}: {detail}")
    return "\n".join(lines).rstrip() + "\n"


def _render_communication_text(communication: Dict[str, Any], *, indent: str) -> List[str]:
    lines: List[str] = []
    primary = communication.get("primary")
    if primary:
        lines.append(f"{indent}primary: {primary}")
    endpoint = communication.get("endpoint")
    if endpoint:
        lines.append(f"{indent}endpoint: {endpoint}")
    transport = communication.get("transport")
    if transport:
        lines.append(f"{indent}transport: {transport}")
    protocol = communication.get("protocol")
    if protocol:
        lines.append(f"{indent}protocol: {protocol}")
    invocation_style = communication.get("invocation_style")
    if invocation_style:
        lines.append(f"{indent}invocation_style: {invocation_style}")
    surfaces = communication.get("surfaces")
    if isinstance(surfaces, list) and surfaces:
        lines.append(f"{indent}surfaces:")
        for surface in surfaces:
            if not isinstance(surface, dict):
                lines.append(f"{indent}  - {surface}")
                continue
            name = surface.get("name") or "unnamed"
            lines.append(f"{indent}  - {name}")
            for key in ("transport", "endpoint", "protocol", "invocation_style"):
                value = surface.get(key)
                if value is not None:
                    lines.append(f"{indent}    {key}: {value}")
            auth = surface.get("auth")
            if auth is not None:
                lines.append(f"{indent}    auth: {auth}")
            options = surface.get("options")
            if options is not None:
                lines.append(f"{indent}    options: {options}")
    return lines
