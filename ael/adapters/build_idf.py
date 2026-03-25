import os
import shutil
import subprocess

from ael.connection_model import _as_board_dict


def _idf_ok():
    return shutil.which("idf.py") is not None


def _inject_idf_path(idf_path: str) -> bool:
    """Add IDF tools to PATH by sourcing export.sh (or using idf_path/tools directly)."""
    export_sh = os.path.join(idf_path, "export.sh")
    if not os.path.exists(export_sh):
        return False
    # Extract PATH additions by sourcing export.sh in a subprocess
    result = subprocess.run(
        f'source "{export_sh}" 2>/dev/null && echo "IDF_PATH=$IDF_PATH" && echo "PATH=$PATH"',
        shell=True, executable="/bin/bash",
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if line.startswith("PATH="):
            os.environ["PATH"] = line[len("PATH="):]
        elif line.startswith("IDF_PATH="):
            os.environ["IDF_PATH"] = line[len("IDF_PATH="):]
    return _idf_ok()


def run(board_cfg):
    board_cfg = _as_board_dict(board_cfg)
    name = board_cfg.get("name", "unknown")
    build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg, dict) else {}
    project_dir = build_cfg.get("project_dir")
    target = build_cfg.get("target") or build_cfg.get("idf_target") or board_cfg.get("target")
    build_dir_override = str(build_cfg.get("build_dir") or "").strip()
    print(f"Build: target {name}")

    if not _idf_ok():
        # Try idf_path from build config, then from environment
        idf_path = (
            build_cfg.get("idf_path")
            or board_cfg.get("idf_path")
            or os.environ.get("IDF_PATH")
        )
        if idf_path and _inject_idf_path(idf_path):
            print(f"Build: IDF sourced from {idf_path}")
        else:
            print("Build: idf.py not found in PATH")
            return None

    if not project_dir:
        print("Build: project_dir not set")
        return None

    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    proj = os.path.join(root, project_dir)
    target_name = str(target or "esp32s3").strip()
    if build_dir_override:
        build_dir = os.path.join(root, build_dir_override)
    else:
        build_dir = os.path.join(root, "artifacts", f"build_{target_name}")
    # If the build dir exists but lacks CMakeCache.txt it is a partial or stale
    # directory.  IDF's fullclean (triggered by set-target) refuses to remove
    # directories it cannot identify as a CMake build tree, causing a hard
    # failure.  Remove it ourselves so IDF can start clean.
    cmake_cache = os.path.join(build_dir, "CMakeCache.txt")
    if os.path.isdir(build_dir) and not os.path.exists(cmake_cache):
        print(f"Build: removing partial build dir {build_dir}")
        shutil.rmtree(build_dir)
    os.makedirs(build_dir, exist_ok=True)

    # skip_set_target: set true for brownfield projects that already have a
    # tuned sdkconfig. Running set-target triggers fullclean + sdkconfig
    # regeneration which destroys project-specific settings.
    skip_set_target = bool(build_cfg.get("skip_set_target", False))

    try:
        env = os.environ.copy()
        if target:
            env["IDF_TARGET"] = str(target)
        if target and not skip_set_target:
            res = subprocess.run(
                ["idf.py", "-C", proj, "-B", build_dir, "set-target", str(target)],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            if res.stdout:
                print(res.stdout.strip())
            if res.stderr:
                print(res.stderr.strip())
        elif skip_set_target:
            print(f"Build: skip_set_target=true — using existing sdkconfig")
        res = subprocess.run(
            ["idf.py", "-C", proj, "-B", build_dir, "build"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
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

    elf = os.path.join(build_dir, f"ael_{target_name}.elf")
    if not os.path.exists(elf):
        # fallback to any .elf under build dir
        for f in os.listdir(build_dir):
            if f.endswith(".elf"):
                elf = os.path.join(build_dir, f)
                break
    if not os.path.exists(elf):
        print("Build: FAIL (elf not found)")
        return None

    print(f"Build: OK -> {elf}")
    return elf
