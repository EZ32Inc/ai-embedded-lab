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

from orchestrator import run_cli, run_pipeline, _simple_yaml_load, _normalize_probe_cfg
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

    pack_p = sub.add_parser("pack")
    pack_p.add_argument("--pack", required=True)
    pack_p.add_argument("--board", required=False)
    pack_p.add_argument("--stop-on-fail", action="store_true")
    pack_p.add_argument("--no-flash", action="store_true")
    pack_p.add_argument("--no-build", action="store_true")
    pack_p.add_argument("--verify-only", action="store_true")

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
    if args.cmd == "pack":
        code = run_pack(
            pack_path=args.pack,
            board_override=args.board,
            stop_on_fail=args.stop_on_fail,
            no_flash=args.no_flash,
            no_build=args.no_build,
            verify_only=args.verify_only,
        )
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


def _git_describe():
    try:
        res = subprocess.run(
            ["git", "describe", "--always", "--dirty", "--tags"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            return (res.stdout or "").strip()
    except Exception:
        pass
    return ""


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def run_pack(pack_path, board_override=None, stop_on_fail=False, no_flash=False, no_build=False, verify_only=False):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    pack_full = pack_path if os.path.isabs(pack_path) else os.path.join(repo_root, pack_path)
    pack = _load_json(pack_full)

    pack_name = pack.get("name", "pack")
    pack_board = board_override or pack.get("board")
    tests = pack.get("tests", [])
    if not pack_board or not tests:
        print("Pack: missing board or tests")
        return 2

    # Validate tests for mixed boards
    for t in tests:
        t_full = t if os.path.isabs(t) else os.path.join(repo_root, t)
        t_json = _load_json(t_full)
        t_board = t_json.get("board") if isinstance(t_json, dict) else None
        if t_board and t_board != pack_board:
            print(f"Pack: test {t} targets board {t_board}, expected {pack_board}")
            return 3

    bench_path = os.path.join(repo_root, "configs", "bench.yaml")
    bench = _simple_yaml_load(bench_path)

    run_id = f"{datetime.now():%Y-%m-%d_%H-%M-%S}_{pack_name}_{pack_board}"
    pack_root = os.path.join(repo_root, "pack_runs", run_id)
    os.makedirs(pack_root, exist_ok=True)

    meta = {
        "timestamp": datetime.now().isoformat(),
        "git_describe": _git_describe(),
        "bench": bench,
        "pack": pack_name,
        "board": pack_board,
    }
    plan = {"tests": tests}
    result = {"ok": True, "results": []}

    def _write(path, data):
        with open(os.path.join(pack_root, path), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    _write("pack_meta.json", meta)
    _write("pack_plan.json", plan)
    _write("pack_result.json", result)

    for t in tests:
        t_full = t if os.path.isabs(t) else os.path.join(repo_root, t)
        code, run_paths = run_pipeline(
            probe_path=os.path.join(repo_root, "configs", "esp32jtag.yaml"),
            board_arg=pack_board,
            test_path=t_full,
            wiring=None,
            output_mode="normal",
            skip_flash=no_flash or verify_only,
            no_build=no_build or verify_only,
            verify_only=verify_only,
            return_paths=True,
        )
        run_result = _load_json(run_paths.result)
        entry = {
            "test": t,
            "run_dir": str(run_paths.root),
            "ok": bool(run_result.get("ok")),
            "failed_step": run_result.get("failed_step", ""),
            "code": code,
        }
        result["results"].append(entry)
        result["ok"] = result["ok"] and entry["ok"]
        _write("pack_result.json", result)
        if stop_on_fail and not entry["ok"]:
            break

    # HTML report
    report = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Pack Report</title></head><body>",
        f"<h1>Pack {pack_name}</h1>",
        f"<p>Board: {pack_board}</p>",
        "<ul>",
    ]
    for r in result["results"]:
        run_dir = r["run_dir"]
        report.append(
            f\"<li>{r['test']} — {'OK' if r['ok'] else 'FAIL'} — \"
            f\"<a href=\\\"file://{run_dir}\\\">{run_dir}</a></li>\"
        )
    report.extend(["</ul>", "</body></html>"])
    with open(os.path.join(pack_root, "pack_report.html"), "w", encoding="utf-8") as f:
        f.write(\"\\n\".join(report))

    return 0 if result["ok"] else 1
