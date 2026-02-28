import json
import os
import subprocess
import time


def _run_gdb(gdb_cmd, ip, port, firmware_path, target_id, pre_cmds, post_cmds, timeout_s, do_continue):
    args = [
        gdb_cmd,
        "-q",
        "--nx",
        "--batch",
        "-ex",
        f"target extended-remote {ip}:{port}",
    ]
    for cmd in pre_cmds:
        args.extend(["-ex", cmd])
    args.extend(
        [
            "-ex",
            "monitor a",
            "-ex",
            f"file {firmware_path}",
            "-ex",
            f"attach {target_id}",
            "-ex",
            "load",
        ]
    )
    for cmd in post_cmds:
        args.extend(["-ex", cmd])
    if do_continue:
        args.extend(["-ex", "monitor reset run", "-ex", "continue", "-ex", "detach"])
    else:
        args.extend(["-ex", "detach"])
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout_s)


def _run_continue(gdb_cmd, ip, port, target_id, timeout_s):
    args = [
        gdb_cmd,
        "-q",
        "--nx",
        "--batch",
        "-ex",
        f"target extended-remote {ip}:{port}",
        "-ex",
        "monitor a",
        "-ex",
        f"attach {target_id}",
        "-ex",
        "continue",
        "-ex",
        "detach",
    ]
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout_s)


def run(probe_cfg, firmware_path, flash_cfg=None, flash_json_path=None):
    if not firmware_path or not os.path.exists(firmware_path):
        print("Flash: firmware not found")
        return False

    ip = probe_cfg.get("ip")
    port = probe_cfg.get("gdb_port")
    gdb_cmd = probe_cfg.get("gdb_cmd")

    if not gdb_cmd:
        print("Flash: gdb_cmd not set")
        return False

    flash_cfg = flash_cfg or {}
    target_id = flash_cfg.get("target_id", 1)
    speed_khz = flash_cfg.get("speed_khz", None)
    reset_strategy = flash_cfg.get("reset_strategy", "")
    timeout_s = int(flash_cfg.get("timeout_s", 120))
    do_continue = True

    attempts = []
    strategies = [
        {
            "name": "normal",
            "pre": [],
            "post": [],
        },
        {
            "name": "connect_under_reset",
            "pre": ["monitor connect_srst enable", "monitor reset halt"],
            "post": ["monitor connect_srst disable"],
        },
        {
            "name": "reduced_speed",
            "pre": ([f"monitor swd_freq {int(speed_khz)}"] if speed_khz else []),
            "post": [],
        },
        {
            "name": "reconnect",
            "pre": ["monitor reconnect"],
            "post": [],
        },
    ]

    if reset_strategy and reset_strategy != "connect_under_reset":
        # If a custom reset strategy is set, only include it as attempt 2.
        strategies[1]["name"] = reset_strategy

    print("Flash: BMDA via GDB (resilience ladder)")
    ok = False
    strategy_used = ""
    last_error = ""

    for idx, strat in enumerate(strategies, start=1):
        try:
            res = _run_gdb(
                gdb_cmd,
                ip,
                port,
                firmware_path,
                target_id,
                strat.get("pre", []),
                strat.get("post", []),
                timeout_s,
                do_continue,
            )
            out = (res.stdout or "") + (res.stderr or "")
            out_l = out.lower()
            attempt_ok = res.returncode == 0 and "failed" not in out_l
            attempts.append(
                {
                    "attempt": idx,
                    "strategy": strat.get("name"),
                    "ok": attempt_ok,
                    "returncode": res.returncode,
                }
            )
            print(f"Flash: attempt {idx} ({strat.get('name')}) -> " + ("OK" if attempt_ok else "FAIL"))
            if res.stdout:
                print(res.stdout.strip())
            if res.stderr:
                print(res.stderr.strip())
            if attempt_ok:
                ok = True
                strategy_used = strat.get("name")
                # If the probe reports a remote failure, try a delayed continue.
                if "remote failure reply" in out_l or "could not read registers" in out_l:
                    print("Flash: warning - remote failure reply, retrying continue")
                    time.sleep(0.5)
                    try:
                        res2 = _run_continue(gdb_cmd, ip, port, target_id, timeout_s)
                        if res2.stdout:
                            print(res2.stdout.strip())
                        if res2.stderr:
                            print(res2.stderr.strip())
                    except Exception as exc:
                        print(f"Flash: continue retry error ({exc})")
                break
            last_error = "flash attempt failed"
        except Exception as exc:
            attempts.append(
                {
                    "attempt": idx,
                    "strategy": strat.get("name"),
                    "ok": False,
                    "error": str(exc),
                }
            )
            last_error = str(exc)
        time.sleep(0.2)

    if not ok:
        print("Flash: FAIL")
    else:
        print("Flash: OK")

    if flash_json_path:
        payload = {
            "ok": ok,
            "attempts": attempts,
            "strategy_used": strategy_used,
            "speed_khz": speed_khz,
            "target_id": target_id,
            "reset_strategy": reset_strategy,
            "error_summary": last_error,
        }
        try:
            with open(flash_json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=True)
        except Exception:
            pass

    return ok
