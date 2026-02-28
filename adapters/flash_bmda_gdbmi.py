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

    print("Flash: BMDA via GDB")
    try:
        res = subprocess.run(
            [
                gdb_cmd,
                "-q",
                "--nx",
                "--batch",
                "-ex",
                f"target extended-remote {ip}:{port}",
                "-ex",
                "monitor a",
                "-ex",
                f"file {firmware_path}",
                "-ex",
                "attach 1",
                "-ex",
                "load",
                "-ex",
                "monitor reset run",
                "-ex",
                "detach",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        out = (res.stdout or "") + (res.stderr or "")
        out_l = out.lower()
        ok = res.returncode == 0 and "failed" not in out_l

        print("Flash: " + ("OK" if ok else "FAIL"))
        if res.stdout:
            print(res.stdout.strip())
        if res.stderr:
            print(res.stderr.strip())
        return ok
    except Exception as exc:
        print(f"Flash: error ({exc})")
        return False
