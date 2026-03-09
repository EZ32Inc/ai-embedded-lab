from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ProbeBinding:
    raw: Dict[str, Any]
    config_path: Optional[str]
    instance_id: Optional[str]
    type_id: Optional[str]
    instance_path: Optional[str]
    type_path: Optional[str]
    endpoint_host: Optional[str]
    endpoint_port: Optional[int]
    legacy_warning: Optional[str]


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(out.get(key), dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _abs(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (repo_root / path)


def _int_or_none(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


def load_probe_binding(
    repo_root: str | Path,
    *,
    probe_path: str | None = None,
    instance_id: str | None = None,
) -> ProbeBinding:
    root = Path(repo_root)

    if probe_path:
        candidate = _abs(root, str(probe_path)).resolve()
        try:
            rel = candidate.relative_to(root)
        except Exception:
            rel = None
        if rel is not None and rel.parts[:2] == ("configs", "instrument_instances"):
            instance_id = candidate.stem

    if instance_id:
        instance_rel = Path("configs") / "instrument_instances" / f"{instance_id}.yaml"
        instance_path = (root / instance_rel).resolve()
        instance_raw = _load_yaml(instance_path)
        instance_meta = instance_raw.get("instance", {}) if isinstance(instance_raw.get("instance"), dict) else {}
        type_id = str(instance_meta.get("type") or instance_raw.get("type") or "").strip()
        if not type_id:
            raise FileNotFoundError(f"probe instance missing type: {instance_path}")
        type_rel = Path("configs") / "instrument_types" / f"{type_id}.yaml"
        type_path = (root / type_rel).resolve()
        type_raw = _load_yaml(type_path)
        merged = _deep_merge(type_raw, instance_raw)
        connection = merged.get("connection", {}) if isinstance(merged.get("connection"), dict) else {}
        return ProbeBinding(
            raw=merged,
            config_path=str(instance_path),
            instance_id=str(instance_meta.get("id") or instance_id),
            type_id=type_id,
            instance_path=str(instance_path),
            type_path=str(type_path),
            endpoint_host=str(connection.get("ip") or "") or None,
            endpoint_port=_int_or_none(connection.get("gdb_port")),
            legacy_warning=None,
        )

    probe_abs = _abs(root, str(probe_path or "configs/esp32jtag.yaml")).resolve()
    raw = _load_yaml(probe_abs)
    connection = raw.get("connection", {}) if isinstance(raw.get("connection"), dict) else {}
    legacy_warning = "Using legacy shared probe config; explicit instrument instance is recommended."
    return ProbeBinding(
        raw=raw,
        config_path=str(probe_abs),
        instance_id=None,
        type_id=str(raw.get("probe_type") or "").strip() or None,
        instance_path=None,
        type_path=None,
        endpoint_host=str(connection.get("ip") or "") or None,
        endpoint_port=_int_or_none(connection.get("gdb_port")),
        legacy_warning=legacy_warning,
    )
