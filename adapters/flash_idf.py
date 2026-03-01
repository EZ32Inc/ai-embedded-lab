import json
import os
import subprocess
import glob


def _find_tty_by_serial(serial):
    if not serial:
        return None
    for tty in glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"):
        base = os.path.basename(tty)
        sys_path = f"/sys/class/tty/{base}/device"
        # walk up to find serial
        cur = sys_path
        for _ in range(6):
            serial_path = os.path.join(cur, "serial")
            if os.path.exists(serial_path):
                try:
                    with open(serial_path, "r", encoding="utf-8") as f:
                        val = f.read().strip()
                    if val == serial:
                        return tty
                except Exception:
                    pass
            cur = os.path.dirname(cur)
    return None


def _first_tty():
    for tty in glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"):
        return tty
    return None


def run(probe_cfg, firmware_path, flash_cfg=None, flash_json_path=None):
    flash_cfg = flash_cfg or {}
    project_dir = flash_cfg.get("project_dir")
    port = flash_cfg.get("port")
    baud = flash_cfg.get("baud", 460800)
    serial = flash_cfg.get("serial")

    root = os.path.dirname(os.path.dirname(__file__))
    if project_dir:
        proj = os.path.join(root, project_dir)
    else:
        proj = root

    if not port:
        port = _find_tty_by_serial(serial) or _first_tty()

    if not port:
        print("Flash: no serial port found")
        return False

    print(f"Flash: ESP-IDF via idf.py port={port} baud={baud}")
    try:
        res = subprocess.run(
            ["idf.py", "-C", proj, "-p", port, "-b", str(baud), "flash"],
            check=True,
            capture_output=True,
            text=True,
        )
        if res.stdout:
            print(res.stdout.strip())
        if res.stderr:
            print(res.stderr.strip())
        ok = True
    except subprocess.CalledProcessError as exc:
        print("Flash: FAIL")
        if exc.stdout:
            print(exc.stdout.strip())
        if exc.stderr:
            print(exc.stderr.strip())
        ok = False

    if flash_json_path:
        payload = {
            "ok": ok,
            "method": "idf_esptool",
            "port": port,
            "baud": baud,
            "serial": serial,
        }
        try:
            with open(flash_json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=True)
        except Exception:
            pass

    return ok
