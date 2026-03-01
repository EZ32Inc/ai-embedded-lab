import os
import shutil
import subprocess


def _idf_ok():
    return shutil.which("idf.py") is not None


def run(board_cfg):
    name = board_cfg.get("name", "unknown")
    build_cfg = board_cfg.get("build", {}) if isinstance(board_cfg, dict) else {}
    project_dir = build_cfg.get("project_dir")
    print(f"Build: target {name}")

    if not _idf_ok():
        print("Build: idf.py not found in PATH")
        return None

    if not project_dir:
        print("Build: project_dir not set")
        return None

    root = os.path.dirname(os.path.dirname(__file__))
    proj = os.path.join(root, project_dir)
    build_dir = os.path.join(root, "artifacts", "build_esp32s3")
    os.makedirs(build_dir, exist_ok=True)

    try:
        res = subprocess.run(
            ["idf.py", "-C", proj, "-B", build_dir, "build"],
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

    elf = os.path.join(build_dir, "ael_esp32s3.elf")
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
