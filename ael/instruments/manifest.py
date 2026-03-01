import json
from pathlib import Path
from typing import Dict, Optional


SCHEMA_ID = "ael.instrument.manifest.v0.1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _validate_manifest(data: dict) -> bool:
    if not isinstance(data, dict):
        return False
    if data.get("schema") != SCHEMA_ID:
        return False
    if data.get("kind") != "instrument":
        return False
    if not data.get("id"):
        return False
    transports = data.get("transports")
    capabilities = data.get("capabilities")
    if not isinstance(transports, list) or not transports:
        return False
    if not isinstance(capabilities, list) or not capabilities:
        return False
    return True


def load_manifest_from_file(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    if not _validate_manifest(data):
        return None
    return data


def load_manifests() -> Dict[str, dict]:
    repo_root = _repo_root()
    manifests: Dict[str, dict] = {}

    def _load_from_dir(base: Path, origin: str) -> None:
        if not base.exists():
            return
        for mf in base.glob("*/manifest.json"):
            data = load_manifest_from_file(str(mf))
            if not data:
                continue
            data = dict(data)
            data["_origin"] = origin
            data["_path"] = str(mf)
            manifests[data["id"]] = data

    user_dir = repo_root / "assets_user" / "instruments"
    golden_dir = repo_root / "assets_golden" / "instruments"

    _load_from_dir(golden_dir, "golden")
    _load_from_dir(user_dir, "user")
    return manifests
