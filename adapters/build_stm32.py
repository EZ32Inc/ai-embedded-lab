import os
import shutil
import subprocess


def _toolchain_ok():
    return shutil.which("arm-none-eabi-gcc") is not None


def run(board_cfg):
    name = board_cfg.get("name", "unknown")
    print(f"Build: target {name}")

    if not _toolchain_ok():
        print("Build: arm-none-eabi-gcc not found in PATH")
        return None

    root = os.path.dirname(os.path.dirname(__file__))
    fw_dir = os.path.join(root, "firmware_stm32")
    build_dir = os.path.join(root, "artifacts", "build_stm32")
    os.makedirs(build_dir, exist_ok=True)

    out_elf = os.path.join(build_dir, "stm32f103_app.elf")
    out_bin = os.path.join(build_dir, "stm32f103_app.bin")

    try:
        res = subprocess.run(
            ["make", "-C", fw_dir, f"BUILD_DIR={build_dir}", f"OUT_ELF={out_elf}", f"OUT_BIN={out_bin}"],
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

    if not os.path.exists(out_elf):
        print("Build: FAIL (elf not found)")
        return None

    print(f"Build: OK -> {out_elf}")
    return out_elf
