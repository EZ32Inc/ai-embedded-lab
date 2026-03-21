import os
import shutil
from pathlib import Path


_REQUIRED_FIELDS = [
    "id",
    "mcu_or_processors",   # accepts mcu (legacy) or processors[] (new)
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
        elif field == "mcu_or_processors":
            # Accept either processors[] (new) or mcu (legacy)
            if not isinstance(manifest, dict):
                missing.append("mcu")
            elif not manifest.get("processors") and not manifest.get("mcu"):
                missing.append("mcu (or processors)")
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
    # Build target_ids: accepts both mcu (legacy) and processors[] (new)
    processors = (query or {}).get("processors") or []
    target_ids = {p.get("id") or p.get("target") for p in processors if isinstance(p, dict)} - {None}
    if mcu:
        target_ids.add(mcu)
    candidates = list_duts("assets_golden/duts")

    def score(entry):
        manifest = entry.get("manifest") or {}
        s = 0
        # Match against manifest's processors[] or legacy mcu field
        manifest_procs = manifest.get("processors") or []
        manifest_ids = {p.get("id") for p in manifest_procs if isinstance(p, dict)} - {None}
        if not manifest_ids:
            legacy_mcu = manifest.get("mcu")
            if legacy_mcu:
                manifest_ids = {legacy_mcu}
        if target_ids and manifest_ids and target_ids & manifest_ids:
            s += 100
        elif mcu and manifest.get("mcu") == mcu:
            s += 100
        if family and manifest.get("family") == family:
            s += 50
        entry_tags = set(manifest.get("tags", []) or []) if isinstance(manifest, dict) else set()
        s += len(tags.intersection(entry_tags)) * 5
        return s

    candidates.sort(key=score, reverse=True)
    return candidates[0] if candidates and score(candidates[0]) > 0 else None


_VALID_MCU_ROLES = {"dut", "debugger", "coprocessor"}
_VALID_BUILD_TYPES = {"arm_debug", "idf", "cmake", "pico"}
_VALID_FLASH_METHODS = {"gdb_swd", "gdb_stutil", "idf_esptool"}
_VALID_INSTRUMENT_FAMILIES = {"esp32jtag", "stlink", "esp32_meter", "none"}
_VALID_LIFECYCLE_STAGES = {"golden", "draft", "runnable", "validated"}


def validate_dut_manifest(manifest):
    """
    Validate a DUT manifest against the new board-centric spec (dut_spec_v0_1).

    Checks the new structured fields: name, mcus[], board_configs[],
    lifecycle_stage, and their enum constraints.

    Returns a list of error strings. Empty list means valid.
    This is separate from _validate_manifest(), which covers legacy required fields.
    """
    if not isinstance(manifest, dict):
        return ["manifest must be a dict"]

    errors = []

    # name is required in the new spec
    if not manifest.get("name"):
        errors.append("name: required")

    # lifecycle_stage
    ls = manifest.get("lifecycle_stage")
    if ls is not None and ls not in _VALID_LIFECYCLE_STAGES:
        errors.append(f"lifecycle_stage: '{ls}' not in {sorted(_VALID_LIFECYCLE_STAGES)}")

    # mcus[]
    mcus = manifest.get("mcus")
    if mcus is not None:
        if not isinstance(mcus, list) or len(mcus) == 0:
            errors.append("mcus: must be a non-empty list")
        else:
            for i, mcu in enumerate(mcus):
                prefix = f"mcus[{i}]"
                if not isinstance(mcu, dict):
                    errors.append(f"{prefix}: must be a dict")
                    continue
                if not mcu.get("id"):
                    errors.append(f"{prefix}.id: required")
                if not mcu.get("mcu"):
                    errors.append(f"{prefix}.mcu: required")
                if not mcu.get("family"):
                    errors.append(f"{prefix}.family: required")
                role = mcu.get("role")
                if not role:
                    errors.append(f"{prefix}.role: required")
                elif role not in _VALID_MCU_ROLES:
                    errors.append(f"{prefix}.role: '{role}' not in {sorted(_VALID_MCU_ROLES)}")
                # build and flash required for dut role
                if role == "dut":
                    build = mcu.get("build")
                    if not isinstance(build, dict):
                        errors.append(f"{prefix}.build: required for role=dut")
                    else:
                        bt = build.get("type")
                        if not bt:
                            errors.append(f"{prefix}.build.type: required")
                        elif bt not in _VALID_BUILD_TYPES:
                            errors.append(f"{prefix}.build.type: '{bt}' not in {sorted(_VALID_BUILD_TYPES)}")
                        if not build.get("project_dir"):
                            errors.append(f"{prefix}.build.project_dir: required")
                    flash = mcu.get("flash")
                    if not isinstance(flash, dict):
                        errors.append(f"{prefix}.flash: required for role=dut")
                    else:
                        fm = flash.get("method")
                        if not fm:
                            errors.append(f"{prefix}.flash.method: required")
                        elif fm not in _VALID_FLASH_METHODS:
                            errors.append(f"{prefix}.flash.method: '{fm}' not in {sorted(_VALID_FLASH_METHODS)}")

    # board_configs[]
    board_configs = manifest.get("board_configs")
    if board_configs is not None:
        if not isinstance(board_configs, list) or len(board_configs) == 0:
            errors.append("board_configs: must be a non-empty list")
        else:
            for i, bc in enumerate(board_configs):
                prefix = f"board_configs[{i}]"
                if not isinstance(bc, dict):
                    errors.append(f"{prefix}: must be a dict")
                    continue
                if not bc.get("id"):
                    errors.append(f"{prefix}.id: required")
                if not bc.get("path"):
                    errors.append(f"{prefix}.path: required")
                idf = bc.get("instrument_family")
                if not idf:
                    errors.append(f"{prefix}.instrument_family: required")
                elif idf not in _VALID_INSTRUMENT_FAMILIES:
                    errors.append(f"{prefix}.instrument_family: '{idf}' not in {sorted(_VALID_INSTRUMENT_FAMILIES)}")

    return errors


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
