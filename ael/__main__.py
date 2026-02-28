import argparse
import os
import sys
import json
import shutil
import subprocess
from datetime import datetime
import base64
import ssl
import urllib.request

from orchestrator import run_cli, _simple_yaml_load, _normalize_probe_cfg
from ael import run_manager


def main():
    parser = argparse.ArgumentParser(prog="ael")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--test", required=True)
    run_p.add_argument("--board", required=False, help="Board id (e.g. rp2040_pico)")
    run_p.add_argument("--probe", default=os.path.join("configs", "esp32jtag.yaml"))
    run_p.add_argument("--wiring", required=False)
    out_group = run_p.add_mutually_exclusive_group()
    out_group.add_argument("--quiet", action="store_true", help="Concise console output")
    out_group.add_argument("--verbose", action="store_true", help="Verbose console output")

    doc_p = sub.add_parser("doctor")
    doc_p.add_argument("--probe", default=os.path.join("configs", "esp32jtag.yaml"))
    doc_p.add_argument("--board", default=os.path.join("configs", "boards", "rp2040_pico.yaml"))
    doc_p.add_argument("--test", default=os.path.join("tests", "blink_gpio.json"))

    args = parser.parse_args()
    if args.cmd == "run":
        if args.verbose:
            output_mode = "verbose"
        elif args.quiet:
            output_mode = "quiet"
        else:
            output_mode = "normal"
        code = run_cli(
            probe_path=args.probe,
            board_id=args.board,
            test_path=args.test,
            wiring=args.wiring,
            output_mode=output_mode,
        )
        sys.exit(code)
    if args.cmd == "doctor":
        code = run_doctor(args.probe, args.board, args.test)
        sys.exit(code)


def _check_tools(tools):
    missing = [t for t in tools if shutil.which(t) is None]
    return missing


def _monitor_version(probe_cfg):
    gdb_cmd = probe_cfg.get("gdb_cmd")
    ip = probe_cfg.get("ip")
    port = probe_cfg.get("gdb_port")
    if not gdb_cmd or not ip or not port:
        return False, "missing gdb_cmd/ip/port"
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
                "monitor version",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
        ok = res.returncode == 0
        out = (res.stdout or "") + (res.stderr or "")
        return ok, out.strip()
    except Exception as exc:
        return False, str(exc)


def _la_capture_ok(probe_cfg):
    try:
        ip = probe_cfg.get("ip")
        scheme = probe_cfg.get("web_scheme", "https")
        port = int(probe_cfg.get("web_port", 443))
        user = probe_cfg.get("web_user", "admin")
        password = probe_cfg.get("web_pass", "admin")
        verify_ssl = bool(probe_cfg.get("web_verify_ssl", False))

        base_url = f"{scheme}://{ip}:{port}"
        cfg = {
            "sampleRate": 1_000_000,
            "triggerPosition": 50,
            "triggerEnabled": False,
            "triggerModeOR": True,
            "captureInternalTestSignal": True,
            "channels": ["disabled"] * 16,
        }
        auth = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        headers = {"Content-Type": "application/json", "Authorization": f"Basic {auth}"}
        ctx = ssl.create_default_context()
        if not verify_ssl:
            ctx = ssl._create_unverified_context()  # nosec - local device API

        req = urllib.request.Request(
            f"{base_url}/la_configure",
            data=json.dumps(cfg).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            resp.read()

        req = urllib.request.Request(
            f"{base_url}/instant_capture",
            headers={"Authorization": f"Basic {auth}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            blob = resp.read()
        ok = len(blob or b"") > 10
        return ok, f"len={len(blob or b'')}"
    except Exception as exc:
        return False, str(exc)


def _validate_config(probe_raw, board_raw, test_raw):
    issues = []
    probe = probe_raw.get("probe", {}) if isinstance(probe_raw, dict) else {}
    if not probe.get("name"):
        issues.append("probe.name missing")
    conn = probe_raw.get("connection", {}) if isinstance(probe_raw, dict) else {}
    if not (probe.get("ip") or conn.get("ip")):
        issues.append("probe ip missing")
    if not (probe.get("gdb_port") or conn.get("gdb_port")):
        issues.append("probe gdb_port missing")

    board = board_raw.get("board", {}) if isinstance(board_raw, dict) else {}
    if not board.get("name"):
        issues.append("board.name missing")
    if not board.get("target"):
        issues.append("board.target missing")
    if not board.get("default_wiring"):
        issues.append("board.default_wiring missing")
    if not board.get("safe_pins"):
        issues.append("board.safe_pins missing")
    if not board.get("observe_map"):
        issues.append("board.observe_map missing")
    if not board.get("flash"):
        issues.append("board.flash missing")

    if isinstance(test_raw, dict):
        if not test_raw.get("name"):
            issues.append("test.name missing")
        if not test_raw.get("pin"):
            issues.append("test.pin missing")
        if test_raw.get("min_freq_hz") is None:
            issues.append("test.min_freq_hz missing")
        if test_raw.get("max_freq_hz") is None:
            issues.append("test.max_freq_hz missing")
        if test_raw.get("duty_min") is None:
            issues.append("test.duty_min missing")
        if test_raw.get("duty_max") is None:
            issues.append("test.duty_max missing")
    return issues


def run_doctor(probe_path, board_path, test_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    run_paths = run_manager.create_run("doctor", "doctor", repo_root)

    # Prepare log and result.
    run_manager.ensure_parent(run_paths.doctor_log)
    result = {
        "ok": False,
        "failed_step": "",
        "error_summary": "",
        "logs": {"doctor": str(run_paths.doctor_log)},
    }
    run_manager.ensure_parent(run_paths.result)
    with open(run_paths.result, "w", encoding="utf-8") as f:
        json.dump(result, f)

    probe_full = probe_path if os.path.isabs(probe_path) else os.path.join(repo_root, probe_path)
    board_full = board_path if os.path.isabs(board_path) else os.path.join(repo_root, board_path)
    test_full = test_path if os.path.isabs(test_path) else os.path.join(repo_root, test_path)

    probe_raw = _simple_yaml_load(probe_full)
    board_raw = _simple_yaml_load(board_full)
    test_raw = {}
    try:
        with open(test_full, "r", encoding="utf-8") as f:
            test_raw = json.load(f)
    except Exception:
        test_raw = {}

    probe_cfg = _normalize_probe_cfg(probe_raw)

    with open(run_paths.doctor_log, "w", encoding="utf-8") as logf:
        tee = run_manager.Tee(logf, sys.stdout, "normal")
        orig_out = sys.stdout
        sys.stdout = tee
        try:
            print("Doctor: starting checks")
            missing = _check_tools(["arm-none-eabi-gdb", "arm-none-eabi-gcc", "cmake"])
            if missing:
                print("Doctor: missing tools: " + ", ".join(missing))
            else:
                print("Doctor: tools OK")

            ok_bmp, bmp_info = _monitor_version(probe_cfg)
            print("Doctor: BMP monitor -> " + ("OK" if ok_bmp else "FAIL"))
            if bmp_info:
                print(bmp_info)

            ok_la, la_info = _la_capture_ok(probe_cfg)
            print("Doctor: LA capture -> " + ("OK" if ok_la else "FAIL"))
            if la_info:
                print(la_info)

            issues = _validate_config(probe_raw, board_raw, test_raw)
            if issues:
                print("Doctor: config issues:")
                for item in issues:
                    print(" - " + item)
            else:
                print("Doctor: config OK")

            overall_ok = (not missing) and ok_bmp and ok_la and (not issues)
            result["ok"] = overall_ok
            result["failed_step"] = "" if overall_ok else "doctor"
            result["error_summary"] = "" if overall_ok else "doctor failed"
            with open(run_paths.result, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, sort_keys=True)
        finally:
            sys.stdout.flush()
            sys.stdout = orig_out

    meta = {
        "run_id": run_paths.run_id,
        "started_at": datetime.now().isoformat(),
        "probe_path": probe_path,
        "board_path": board_path,
        "test_path": test_path,
    }
    with open(run_paths.meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    main()
