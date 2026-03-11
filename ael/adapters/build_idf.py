import os
import shutil
import subprocess


def _idf_ok():
    return shutil.which("idf.py") is not None


def run(board_cfg):
    name = board_cfg.get("name", "unknown")
    build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg, dict) else {}
    project_dir = build_cfg.get("project_dir")
    target = build_cfg.get("target") or board_cfg.get("target")
    build_dir_override = str(build_cfg.get("build_dir") or "").strip()
    print(f"Build: target {name}")

    if not _idf_ok():
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
    os.makedirs(build_dir, exist_ok=True)

    try:
        env = os.environ.copy()
        if target:
            env["IDF_TARGET"] = str(target)
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
