from __future__ import annotations

import os
from typing import Any, Dict, Optional


_WIRING_FIELDS = ("bench_connections", "observe_map", "verification_views", "default_wiring", "safe_pins")


def resolve_bench_profile_id(
    board_raw: Dict[str, Any],
    pack_meta: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Returns the bench profile id to load.
    Priority: pack_meta["bench_profile"] > board_raw["board"]["default_bench_profile"] > None
    """
    if isinstance(pack_meta, dict):
        profile_id = pack_meta.get("bench_profile")
        if profile_id and str(profile_id).strip():
            return str(profile_id).strip()
    if isinstance(board_raw, dict):
        board_section = board_raw.get("board", {})
        if isinstance(board_section, dict):
            profile_id = board_section.get("default_bench_profile")
            if profile_id and str(profile_id).strip():
                return str(profile_id).strip()
    return None


def load_bench_profile(repo_root: str, profile_id: str) -> Dict[str, Any]:
    """
    Loads configs/bench_profiles/{profile_id}.yaml.
    Returns the dict under the top-level "bench_profile" key.
    Raises FileNotFoundError if not found.
    """
    path = os.path.join(repo_root, "configs", "bench_profiles", f"{profile_id}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"bench profile not found: {path}")
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        raise ValueError(f"failed to load bench profile {profile_id}: {exc}") from exc
    if not isinstance(data, dict) or "bench_profile" not in data:
        raise ValueError(f"bench profile {profile_id} missing top-level 'bench_profile' key")
    result = data["bench_profile"]
    if not isinstance(result, dict):
        raise ValueError(f"bench profile {profile_id}: 'bench_profile' must be a mapping")
    return result


def resolve_bench_wiring_fields(
    repo_root: str,
    board_raw: Dict[str, Any],
    pack_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Returns a dict with keys: bench_connections, observe_map,
    verification_views, default_wiring, safe_pins.

    Resolution order:
    1. If bench_profile_id resolves → load profile file → return its fields.
    2. Else if board_raw["board"] has inline wiring fields → return those.
    3. Else return empty dict.
    """
    profile_id = resolve_bench_profile_id(board_raw, pack_meta=pack_meta)
    if profile_id:
        profile = load_bench_profile(repo_root, profile_id)
        return {field: profile[field] for field in _WIRING_FIELDS if field in profile}
    # Tier 3: inline fields already in board_raw["board"]
    if isinstance(board_raw, dict):
        board_section = board_raw.get("board", {})
        if isinstance(board_section, dict):
            return {field: board_section[field] for field in _WIRING_FIELDS if field in board_section}
    return {}
