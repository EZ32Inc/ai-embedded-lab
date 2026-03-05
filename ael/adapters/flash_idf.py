import json
import os
import subprocess
import glob
import time


def _find_tty_by_serial(serial):
    if not serial:
        return None
    serial_norm = str(serial).strip().lower()
    for tty in glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"):
        base = os.path.basename(tty)
        sys_path = f"/sys/class/tty/{base}/device"
        # walk up to find serial
        cur = os.path.realpath(sys_path)
        for _ in range(6):
            serial_path = os.path.join(cur, "serial")
            if os.path.exists(serial_path):
                try:
                    with open(serial_path, "r", encoding="utf-8") as f:
                        val = f.read().strip()
                    if val.strip().lower() == serial_norm:
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
    build_dir = flash_cfg.get("build_dir")
    target = flash_cfg.get("target")
    port = flash_cfg.get("port")
    baud = flash_cfg.get("baud", 460800)
    serial = flash_cfg.get("serial")
    target = str(flash_cfg.get("target") or "esp32s3")
    # Keep optional workaround disabled by default. Standard `idf.py flash`
    # already performs a hard reset and should hand off to app mode.
    post_flash_run = bool(flash_cfg.get("post_flash_run", False))

    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if project_dir:
        proj = os.path.join(root, project_dir)
    else:
        proj = root

    if not build_dir and target:
        build_dir = os.path.join(root, "artifacts", f"build_{target}")

    if not port:
        port = _find_tty_by_serial(serial) or _first_tty()

    if not port:
        print("Flash: no serial port found")
        return False

    print(f"Flash: ESP-IDF via idf.py port={port} baud={baud}")
    try:
        cmd = ["idf.py", "-C", proj]
        if build_dir:
            cmd += ["-B", build_dir]
        cmd += ["-p", port, "-b", str(baud), "flash"]
        res = subprocess.run(
            cmd,
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

    if ok and post_flash_run:
        # On some ESP32-S3 native USB setups, flash hard-reset leaves ROM downloader active.
        # Kick the chip into app mode without external line toggles.
        run_cmd = [
            "python3",
            "-m",
            "esptool",
            "--chip",
            target,
            "-p",
            str(port),
            "--before",
            "no_reset",
            "--after",
            "watchdog_reset",
            "run",
        ]
        run_ok = False
        last_exc = None
        for attempt in range(1, 9):
            try:
                run_res = subprocess.run(run_cmd, check=True, capture_output=True, text=True, timeout=20)
                print(f"Flash: post-flash run via watchdog reset (attempt {attempt})")
                if run_res.stdout:
                    print(run_res.stdout.strip())
                if run_res.stderr:
                    print(run_res.stderr.strip())
                run_ok = True
                break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                last_exc = exc
                time.sleep(0.4)
        if not run_ok:
            print("Flash: WARN post-flash run failed")
            if isinstance(last_exc, subprocess.CalledProcessError):
                if last_exc.stdout:
                    print(last_exc.stdout.strip())
                if last_exc.stderr:
                    print(last_exc.stderr.strip())

    if flash_json_path:
        payload = {
            "ok": ok,
            "method": "idf_esptool",
            "port": port,
            "baud": baud,
            "serial": serial,
            "build_dir": build_dir,
        }
        try:
            with open(flash_json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=True)
        except Exception:
            pass

    return ok
