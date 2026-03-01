import os
import shutil
from pathlib import Path


_REQUIRED_FIELDS = [
    "id",
    "mcu",
    "family",
    "description",
    ("build", "type"),
    ("build", "project_dir"),
    ("flash", "method"),
    ("verified", "status"),
]


def _load_yaml(path: Path):
    try:
        import yaml  # type: ignore

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        data = {}
        stack = [data]
        indent_stack = [0]
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if not line.strip() or line.strip().startswith("#"):
                    continue
                indent = len(line) - len(line.lstrip(" "))
                key, _, value = line.strip().partition(":")
                value = value.strip().strip('"')
                while indent < indent_stack[-1]:
                    stack.pop()
                    indent_stack.pop()
                if value == "":
                    obj = {}
                    stack[-1][key] = obj
                    stack.append(obj)
                    indent_stack.append(indent)
                else:
                    if value.startswith("[") and value.endswith("]"):
                        value = [v.strip().strip('"') for v in value[1:-1].split(",") if v.strip()]
                    stack[-1][key] = value
        return data


def _validate_manifest(manifest):
    missing = []
    for field in _REQUIRED_FIELDS:
        if isinstance(field, tuple):
            cur = manifest
            for key in field:
                if not isinstance(cur, dict) or key not in cur:
                    cur = None
                    break
                cur = cur.get(key)
            if cur is None:
                missing.append(".".join(field))
        else:
            if not isinstance(manifest, dict) or field not in manifest:
                missing.append(field)
    return missing


def list_duts(root_dir):
    root = Path(root_dir)
    if not root.exists():
        return []
    duts = []
    for item in root.iterdir():
        if not item.is_dir():
            continue
        manifest_path = item / "manifest.yaml"
        if not manifest_path.exists():
            continue
        manifest = _load_yaml(manifest_path)
        missing = _validate_manifest(manifest)
        entry = {
            "id": manifest.get("id") if isinstance(manifest, dict) else None,
            "path": str(item),
            "manifest": manifest,
            "valid": not missing,
            "missing": missing,
        }
        duts.append(entry)
    return duts


def load_dut(dut_id, roots=None):
    roots = roots or ["assets_golden/duts", "assets_user/duts"]
    for root in roots:
        path = Path(root) / dut_id / "manifest.yaml"
        if path.exists():
            manifest = _load_yaml(path)
            missing = _validate_manifest(manifest)
            return {
                "id": manifest.get("id") if isinstance(manifest, dict) else dut_id,
                "path": str(path.parent),
                "manifest": manifest,
                "valid": not missing,
                "missing": missing,
            }
    return None


def load_dut_prefer_user(dut_id):
    roots = ["assets_user/duts", "assets_golden/duts"]
    return load_dut(dut_id, roots=roots)


def find_golden_reference(query):
    mcu = (query or {}).get("mcu")
    family = (query or {}).get("family")
    tags = set((query or {}).get("tags", []) or [])
    candidates = list_duts("assets_golden/duts")

    def score(entry):
        manifest = entry.get("manifest") or {}
        s = 0
        if mcu and manifest.get("mcu") == mcu:
            s += 100
        if family and manifest.get("family") == family:
            s += 50
        entry_tags = set(manifest.get("tags", []) or []) if isinstance(manifest, dict) else set()
        s += len(tags.intersection(entry_tags)) * 5
        return s

    candidates.sort(key=score, reverse=True)
    return candidates[0] if candidates and score(candidates[0]) > 0 else None


def copy_dut_skeleton(src_dut_path, dst_dut_path):
    src = Path(src_dut_path)
    dst = Path(dst_dut_path)
    if not src.exists():
        raise FileNotFoundError(str(src))
    ignore = shutil.ignore_patterns(
        "build",
        "artifacts",
        "__pycache__",
        ".git",
        "runs",
        "pack_runs",
        "cache",
    )
    if dst.exists():
        raise FileExistsError(str(dst))
    shutil.copytree(src, dst, ignore=ignore, symlinks=True)
    return str(dst)


def save_manifest(path: Path, manifest: dict):
    lines = []

    def emit(key, val, indent=0):
        pad = " " * indent
        if isinstance(val, dict):
            lines.append(f"{pad}{key}:")
            for k, v in val.items():
                emit(k, v, indent + 2)
        elif isinstance(val, list):
            lines.append(f"{pad}{key}:")
            for item in val:
                lines.append(f"{pad}  - {item}")
        elif isinstance(val, bool):
            lines.append(f"{pad}{key}: {'true' if val else 'false'}")
        elif val is None:
            lines.append(f"{pad}{key}: null")
        else:
            lines.append(f"{pad}{key}: {val}")

    for k, v in manifest.items():
        emit(k, v)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
