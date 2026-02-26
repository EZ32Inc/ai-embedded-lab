import os
import subprocess


def run(probe_cfg, firmware_path):
    if not firmware_path or not os.path.exists(firmware_path):
        print("Flash: firmware not found")
        return False

    ip = probe_cfg.get("ip")
    port = probe_cfg.get("gdb_port")
    gdb_cmd = probe_cfg.get("gdb_cmd")

    if not gdb_cmd:
        print("Flash: gdb_cmd not set")
        return False

    print("Flash: BMDA via GDB-MI")
    try:
        res = subprocess.run(
            [
                gdb_cmd,
                "--interpreter=mi2",
                "--quiet",
                "-ex",
                f"target extended-remote {ip}:{port}",
                "-ex",
                "monitor reset halt",
                "-ex",
                f"load {firmware_path}",
                "-ex",
                "monitor reset run",
                "-ex",
                "quit",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        ok = res.returncode == 0
        print("Flash: " + ("OK" if ok else "FAIL"))
        if res.stdout:
            print(res.stdout.strip())
        if res.stderr and not ok:
            print(res.stderr.strip())
        return ok
    except Exception as exc:
        print(f"Flash: error ({exc})")
        return False
