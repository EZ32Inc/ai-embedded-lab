import os
import shutil
import subprocess
from pathlib import Path


def _toolchain_ok():
    return shutil.which("arm-none-eabi-gcc") is not None


def run(board_cfg):
    name = board_cfg.get("name", "unknown")
    print(f"Build: target {name}")

    if not _toolchain_ok():
        print("Build: arm-none-eabi-gcc not found in PATH")
        return None

    root = Path(__file__).resolve().parents[2]
    build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg.get("build"), dict) else {}
    project_dir = str(build_cfg.get("project_dir") or "").strip()
    build_dir_override = str(build_cfg.get("build_dir") or "").strip()
    if not project_dir:
        project_dir = os.path.join("firmware", "targets", "stm32f103")
    fw_dir = Path(project_dir)
    if not fw_dir.is_absolute():
        fw_dir = root / fw_dir
    if not fw_dir.exists():
        print(f"Build: firmware project not found: {fw_dir}")
        return None

    target = str(board_cfg.get("target") or fw_dir.name or "stm32").strip()
    artifact_stem = str(build_cfg.get("artifact_stem") or f"{target}_app").strip()
    if build_dir_override:
        build_dir = root / build_dir_override
    else:
        build_dir = root / "artifacts" / f"build_{target}"
    os.makedirs(build_dir, exist_ok=True)

    out_elf = build_dir / f"{artifact_stem}.elf"
    out_bin = build_dir / f"{artifact_stem}.bin"

    try:
        res = subprocess.run(
            ["make", "-C", str(fw_dir), f"BUILD_DIR={build_dir}", f"OUT_ELF={out_elf}", f"OUT_BIN={out_bin}"],
            check=True,
            capture_output=True,
            text=True,
        )
        if res.stdout:
            print(res.stdout.strip())
        if res.stderr:
            print(res.stderr.strip())
    except subprocess.CalledProcessError as exc:
        print("Build: FAIL")
        if exc.stdout:
            print(exc.stdout.strip())
        if exc.stderr:
            print(exc.stderr.strip())
        return None

    if not out_elf.exists():
        print("Build: FAIL (elf not found)")
        return None

    print(f"Build: OK -> {out_elf}")
    return str(out_elf)
