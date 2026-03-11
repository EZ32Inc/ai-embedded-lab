import os
import shutil
import subprocess


def _resolve_project_dir(root, board_cfg):
    build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg.get("build"), dict) else {}
    project_dir = str(build_cfg.get("project_dir") or "").strip()
    if not project_dir:
        project_dir = os.path.join("firmware", "targets", "rp2040_pico")
    return os.path.join(root, project_dir)


def _resolve_build_dir(root, board_cfg):
    build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg.get("build"), dict) else {}
    target = str(board_cfg.get("target") or "").strip()
    build_dir_name = str(build_cfg.get("build_dir") or "").strip()
    if build_dir_name:
        return os.path.join(root, build_dir_name)
    if target:
        return os.path.join(root, "artifacts", f"build_{target}")
    return os.path.join(root, "artifacts", "build")


def _resolve_artifact_stem(board_cfg):
    build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg.get("build"), dict) else {}
    artifact_stem = str(build_cfg.get("artifact_stem") or "").strip()
    return artifact_stem or "pico_blink"


def _resolve_local_picotool_root(root):
    deps_root = os.path.join(root, "artifacts", "build", "_deps")
    picotool_path = os.path.join(deps_root, "picotool", "picotool")
    if os.path.exists(picotool_path):
        return deps_root
    return None


def _get_pico_sdk_path():
    env_path = os.environ.get("PICO_SDK_PATH")
    if env_path:
        return env_path

    bashrc = os.path.expanduser("~/.bashrc")
    if os.path.exists(bashrc):
        with open(bashrc, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export PICO_SDK_PATH="):
                    return line.split("=", 1)[1].strip().strip('"')
    return None


def _toolchain_ok():
    return shutil.which("arm-none-eabi-gcc") is not None


def run(board_cfg):
    name = board_cfg.get("name", "unknown")
    print(f"Build: target {name}")

    if not _toolchain_ok():
        print("Build: arm-none-eabi-gcc not found in PATH")
        return None

    pico_sdk = _get_pico_sdk_path()
    if not pico_sdk or not os.path.isdir(pico_sdk):
        print("Build: PICO_SDK_PATH not set or invalid")
        return None

    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    fw_dir = _resolve_project_dir(root, board_cfg)
    build_dir = _resolve_build_dir(root, board_cfg)
    artifact_stem = _resolve_artifact_stem(board_cfg)
    os.makedirs(build_dir, exist_ok=True)

    env = os.environ.copy()
    env["PICO_SDK_PATH"] = pico_sdk
    picotool_root = _resolve_local_picotool_root(root)
    if picotool_root:
        env.setdefault("PICOTOOL_FETCH_FROM_GIT_PATH", picotool_root)

    try:
        cfg = subprocess.run(
            ["cmake", "-S", fw_dir, "-B", build_dir, f"-DPICO_SDK_PATH={pico_sdk}"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        if cfg.stdout:
            print(cfg.stdout.strip())
        if cfg.stderr:
            print(cfg.stderr.strip())

        build = subprocess.run(
            ["cmake", "--build", build_dir, "-j", "--verbose"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        if build.stdout:
            print(build.stdout.strip())
        if build.stderr:
            print(build.stderr.strip())
    except subprocess.CalledProcessError as exc:
        print("Build: FAIL")
        if exc.stdout:
            print(exc.stdout.strip())
        if exc.stderr:
            print(exc.stderr.strip())
        return None

    firmware_path = os.path.join(build_dir, f"{artifact_stem}.elf")
    if not os.path.exists(firmware_path):
        print("Build: FAIL (elf not found)")
        return None

    print(f"Build: OK -> {firmware_path}")
    return firmware_path
