from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set


def capability_names(payload: Dict[str, Any] | Any) -> List[str]:
    if not isinstance(payload, dict):
        return []
    caps = payload.get("capabilities")
    if not isinstance(caps, list):
        return []
    out: List[str] = []
    for item in caps:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            out.append(name)
    return out


def communication_surface_names(communication: Dict[str, Any] | Any) -> Set[str]:
    if not isinstance(communication, dict):
        return set()
    surfaces = communication.get("surfaces")
    if isinstance(surfaces, list):
        names: Set[str] = set()
        for item in surfaces:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if name:
                names.add(name)
        return names
    if any(str(communication.get(key) or "").strip() for key in ("transport", "endpoint", "protocol")):
        return {"primary"}
    return set()


def validate_communication(communication: Dict[str, Any] | Any) -> List[str]:
    if communication is None:
        return []
    if not isinstance(communication, dict):
        return ["communication must be a mapping"]

    errors: List[str] = []
    surfaces = communication.get("surfaces")
    if isinstance(surfaces, list):
        names: Set[str] = set()
        if communication.get("primary") is not None and not str(communication.get("primary") or "").strip():
            errors.append("communication.primary must be a non-empty string when set")
        for index, item in enumerate(surfaces):
            if not isinstance(item, dict):
                errors.append(f"communication.surfaces[{index}] must be a mapping")
                continue
            for key in ("name", "transport", "endpoint", "protocol"):
                if not str(item.get(key) or "").strip():
                    errors.append(f"communication.surfaces[{index}].{key} is required")
            name = str(item.get("name") or "").strip()
            if name:
                if name in names:
                    errors.append(f"communication.surfaces duplicate name: {name}")
                names.add(name)
        primary = str(communication.get("primary") or "").strip()
        if primary and primary not in names:
            errors.append(f"communication.primary references unknown surface: {primary}")
        return errors

    simple_keys = ("transport", "endpoint", "protocol")
    present = [key for key in simple_keys if communication.get(key) is not None]
    if present:
        for key in simple_keys:
            if not str(communication.get(key) or "").strip():
                errors.append(f"communication.{key} is required")
    elif communication:
        errors.append("communication must use either simple transport/endpoint/protocol form or surfaces form")
    return errors


def validate_capability_surfaces(
    mapping: Dict[str, Any] | Any,
    *,
    capabilities: Iterable[str] | None = None,
    communication: Dict[str, Any] | Any = None,
) -> List[str]:
    if mapping is None:
        return []
    if not isinstance(mapping, dict):
        return ["capability_surfaces must be a mapping"]

    errors: List[str] = []
    cap_set = {str(item).strip() for item in (capabilities or []) if str(item).strip()}
    valid_surfaces = communication_surface_names(communication)
    for raw_cap, raw_surface in mapping.items():
        cap = str(raw_cap or "").strip()
        surface = str(raw_surface or "").strip()
        if not cap:
            errors.append("capability_surfaces contains an empty capability key")
            continue
        if not surface:
            errors.append(f"capability_surfaces[{cap}] must be a non-empty string")
            continue
        if cap_set and cap not in cap_set:
            errors.append(f"capability_surfaces references unknown capability: {cap}")
        if valid_surfaces and surface not in valid_surfaces:
            errors.append(f"capability_surfaces[{cap}] references unknown surface: {surface}")
    return errors


def resolve_capability_surface(
    capability: str,
    capability_surfaces: Dict[str, Any] | Any,
    communication: Dict[str, Any] | Any,
) -> str | None:
    cap = str(capability or "").strip()
    if not cap or not isinstance(capability_surfaces, dict):
        return None
    surface = capability_surfaces.get(cap)
    text = str(surface or "").strip()
    if not text:
        return None
    valid = communication_surface_names(communication)
    if valid and text not in valid:
        return None
    return text
