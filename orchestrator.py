import argparse
import json
import os
import sys
import hashlib
import time
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from adapters import preflight, build_cmake, flash_bmda_gdbmi, observe_gpio_pin
from ael import run_manager
from tools import la_verify


def _simple_yaml_load(path):
    try:
        import yaml  # type: ignore

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        data = {}
        stack = [data]
        indent_stack = [0]
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if not line.strip() or line.strip().startswith("#"):
                    continue
                indent = len(line) - len(line.lstrip(" "))
                key, _, value = line.strip().partition(":")
                value = value.strip().strip('"')
                while indent < indent_stack[-1]:
                    stack.pop()
                    indent_stack.pop()
                if value == "":
                    obj = {}
                    stack[-1][key] = obj
                    stack.append(obj)
                    indent_stack.append(indent)
                else:
                    stack[-1][key] = value
        return data


def _deep_merge(base, override):
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _parse_wiring(s):
    wiring = {}
    if not s:
        return wiring
    parts = [p.strip() for p in s.split() if p.strip()]
    for part in parts:
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        wiring[k.strip()] = v.strip()
    return wiring


def _normalize_probe_cfg(raw):
    probe = raw.get("probe", {}) if isinstance(raw, dict) else {}
    connection = raw.get("connection", {}) if isinstance(raw, dict) else {}
    cfg = dict(probe)

    if "ip" not in cfg and "ip" in connection:
        cfg["ip"] = connection["ip"]
    if "gdb_port" not in cfg and "gdb_port" in connection:
        cfg["gdb_port"] = connection["gdb_port"]

    if "gdb_cmd" not in cfg:
        cfg["gdb_cmd"] = raw.get("gdb_cmd") if isinstance(raw, dict) else None
    if not cfg.get("gdb_cmd"):
        cfg["gdb_cmd"] = "gdb-multiarch"

    return cfg


def _merge_wiring(defaults, overrides):
    merged = dict(defaults or {})
    merged.update(overrides or {})
    return merged


def _require_wiring(merged, required):
    missing = [k for k in required if k not in merged or not merged[k]]
    if missing:
        for k in missing:
            merged[k] = "UNKNOWN"
        print(f"I am guessing {', '.join(missing)} — please confirm.")
    return merged


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_info():
    info = {"commit": "", "dirty": False, "status": ""}
    try:
        import subprocess

        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            info["commit"] = (res.stdout or "").strip()

        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            status = (res.stdout or "").strip()
            info["status"] = status
            info["dirty"] = bool(status)
    except Exception:
        pass
    return info


def _write_json(path, data):
    try:
        run_manager.ensure_parent(Path(path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    except Exception:
        pass


def _copy_artifacts(firmware_path, artifacts_dir):
    if not firmware_path:
        return []
    copied = []
    base = Path(firmware_path)
    candidates = [base]
    candidates.append(base.with_suffix(".uf2"))
    candidates.append(base.with_suffix(".bin"))
    for p in candidates:
        if p.exists():
            dest = Path(artifacts_dir) / p.name
            try:
                dest.write_bytes(p.read_bytes())
                copied.append(str(dest))
            except Exception:
                pass
    return copied


@contextmanager
def _tee_output(log_path, output_mode):
    tee, f = run_manager.open_tee(Path(log_path), output_mode, console=sys.stdout)
    orig_out = sys.stdout
    orig_err = sys.stderr
    sys.stdout = tee
    sys.stderr = tee
    try:
        yield
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        sys.stdout = orig_out
        sys.stderr = orig_err
        f.close()


def _triage(stage, pre_info):
    print("FAIL: stage=" + stage)
    if stage == "preflight":
        if not pre_info.get("ping_ok"):
            print("Hint: probe not reachable. Check power and Wi-Fi/AP connection.")
        if not pre_info.get("tcp_ok"):
            print("Hint: GDB port closed. Check ESP32JTAG GDB server and IP/port.")
        if not pre_info.get("monitor_ok"):
            print("Hint: GDB server connected but monitor failed. Try power-cycle target and probe.")
        if not pre_info.get("la_ok"):
            print("Hint: LA web API failed. Check web credentials and HTTPS settings.")
        return
    if stage == "build":
        print("Hint: check pico-sdk path, CMake toolchain, and build dependencies.")
        return
    if stage == "flash":
        print("Hint: verify SWD wiring, target power, and only one GDB session connected.")
        print("Hint: try a reset or power-cycle, then rerun.")
        return
    if stage == "verify":
        print("Hint: verify GPIO mapping and wiring for verify pin.")
        print("Hint: if edges are too few, lower LA sample rate or increase blink frequency.")
        return


def _resolve_board_path(repo_root, board_arg):
    if not board_arg:
        return None, None
    p = Path(board_arg)
    if p.exists() and p.is_file():
        return str(p), p.stem
    board_id = board_arg
    board_path = Path(repo_root) / "configs" / "boards" / f"{board_id}.yaml"
    return str(board_path), board_id


def run_pipeline(probe_path, board_arg, test_path, wiring, output_mode="normal", skip_flash=False):
    repo_root = os.path.dirname(__file__)

    if not test_path:
        test_path = os.path.join(repo_root, "tests", "blink_gpio.json")

    test_raw = {}
    try:
        with open(test_path, "r", encoding="utf-8") as f:
            test_raw = json.load(f)
    except Exception:
        test_raw = {}

    board_path, board_id = _resolve_board_path(repo_root, board_arg)
    if not board_id:
        board_id = test_raw.get("board", "unknown") if isinstance(test_raw, dict) else "unknown"
        if board_id and board_id != "unknown":
            board_path, _ = _resolve_board_path(repo_root, board_id)

    run_paths = run_manager.create_run(board_id or "unknown", test_path, repo_root)
    # Ensure all expected files exist even if we fail early.
    for p in [
        run_paths.build_log,
        run_paths.flash_log,
        run_paths.observe_log,
        run_paths.verify_log,
        run_paths.preflight_log,
    ]:
        Path(p).write_text("")
    _write_json(run_paths.measure, {"ok": False, "metrics": {}, "reasons": ["not_run"]})
    _write_json(run_paths.result, {"ok": False, "failed_step": "", "error_summary": ""})

    probe_raw = _simple_yaml_load(probe_path) if probe_path else {}
    board_raw = _simple_yaml_load(board_path) if board_path else {}

    effective = _deep_merge(_deep_merge(probe_raw, board_raw), test_raw)
    _write_json(run_paths.config_effective, effective)

    run_started = datetime.now()
    run_started_mono = time.monotonic()
    git_info = _git_info()

    meta = {
        "run_id": run_paths.run_id,
        "started_at": run_started.isoformat(),
        "probe_path": probe_path,
        "board_path": board_path,
        "test_path": test_path,
        "git_commit": git_info.get("commit"),
        "git_dirty": git_info.get("dirty"),
        "git_status": git_info.get("status"),
    }

    probe_cfg = _normalize_probe_cfg(probe_raw)
    board_cfg = board_raw.get("board", {}) if isinstance(board_raw, dict) else {}

    wiring_overrides = _parse_wiring(wiring or "")
    wiring_cfg = _merge_wiring(board_cfg.get("default_wiring", {}), wiring_overrides)
    wiring_cfg = _require_wiring(wiring_cfg, ["swd", "reset", "verify"])

    timings = {}
    result = {
        "ok": False,
        "failed_step": "",
        "error_summary": "",
        "logs": {
            "preflight": str(run_paths.preflight_log),
            "build": str(run_paths.build_log),
            "flash": str(run_paths.flash_log),
            "observe": str(run_paths.observe_log),
            "verify": str(run_paths.verify_log),
        },
    }

    print("AI: starting pipeline")
    print(f"Using probe: {probe_cfg.get('name', 'unknown')} @ {probe_cfg.get('ip', 'unknown')}:{probe_cfg.get('gdb_port', 'unknown')}")
    print(f"Using board: {board_cfg.get('name', 'unknown')} target={board_cfg.get('target', 'unknown')}")
    print(f"Wiring: swd={wiring_cfg.get('swd')} reset={wiring_cfg.get('reset')} verify={wiring_cfg.get('verify')}")

    pre_info = {}
    with _tee_output(run_paths.preflight_log, output_mode):
        t0 = time.monotonic()
        ok_pre, pre_info = preflight.run(probe_cfg)
        timings["preflight_s"] = round(time.monotonic() - t0, 3)
    pre_info = pre_info or {}
    pre_info["timing_s"] = timings.get("preflight_s", 0)
    _write_json(run_paths.preflight, pre_info)

    if not ok_pre:
        result["failed_step"] = "preflight"
        result["error_summary"] = "preflight failed"
        _triage("preflight", pre_info)
        _write_json(run_paths.result, result)
        meta["ended_at"] = datetime.now().isoformat()
        _write_json(run_paths.meta, meta)
        return 2

    print("SWD and network connection verified. Starting task.")
    if not pre_info.get("targets"):
        print("Preflight: warning - no targets reported by probe.")

    firmware_path = None
    with _tee_output(run_paths.build_log, output_mode):
        t0 = time.monotonic()
        firmware_path = build_cmake.run(board_cfg)
        timings["build_s"] = round(time.monotonic() - t0, 3)

    if not firmware_path:
        result["failed_step"] = "build"
        result["error_summary"] = "build failed"
        _triage("build", pre_info)
        _write_json(run_paths.result, result)
        meta["ended_at"] = datetime.now().isoformat()
        _write_json(run_paths.meta, meta)
        return 3

    if skip_flash:
        with _tee_output(run_paths.flash_log, output_mode):
            print("Flash: SKIPPED (user requested skip)")
        timings["flash_s"] = 0.0
    else:
        with _tee_output(run_paths.flash_log, output_mode):
            t0 = time.monotonic()
            flash_ok = flash_bmda_gdbmi.run(probe_cfg, firmware_path)
            timings["flash_s"] = round(time.monotonic() - t0, 3)

        if not flash_ok:
            result["failed_step"] = "flash"
            result["error_summary"] = "flash failed"
            _triage("flash", pre_info)
            _write_json(run_paths.result, result)
            meta["ended_at"] = datetime.now().isoformat()
            _write_json(run_paths.meta, meta)
            return 4

    capture = {}
    with _tee_output(run_paths.observe_log, output_mode):
        t0 = time.monotonic()
        ok_obs = observe_gpio_pin.run(
            probe_cfg,
            pin=wiring_cfg.get("verify"),
            duration_s=float(test_raw.get("duration_s", 3.0)) if isinstance(test_raw, dict) else 3.0,
            expected_hz=float(test_raw.get("expected_hz", 1.0)) if isinstance(test_raw, dict) else 1.0,
            min_edges=int(test_raw.get("min_edges", 2)) if isinstance(test_raw, dict) else 2,
            max_edges=int(test_raw.get("max_edges", 6)) if isinstance(test_raw, dict) else 6,
            capture_out=capture,
            verify_edges=False,
        )
        timings["observe_s"] = round(time.monotonic() - t0, 3)

    if not ok_obs:
        result["failed_step"] = "observe"
        result["error_summary"] = "observe failed"
        _write_json(run_paths.result, result)
        meta["ended_at"] = datetime.now().isoformat()
        _write_json(run_paths.meta, meta)
        return 5

    measure = {}
    verify_ok = False
    with _tee_output(run_paths.verify_log, output_mode):
        t0 = time.monotonic()
        if capture.get("blob"):
            measure = la_verify.analyze_capture_bytes(
                capture.get("blob"),
                int(capture.get("sample_rate_hz", 0)),
                int(capture.get("bit", 0)),
                min_edges=int(test_raw.get("min_edges", 2)) if isinstance(test_raw, dict) else 2,
            )
            verify_ok = bool(measure.get("ok"))
            metrics = measure.get("metrics", {})
            print(
                "Verify: freq={:.3f}Hz duty={:.3f} jitter_est={:.6f}s".format(
                    metrics.get("freq_hz", 0.0),
                    metrics.get("duty", 0.0),
                    metrics.get("jitter_est", 0.0),
                )
            )
            if not verify_ok:
                print("Verify: FAIL " + ", ".join(measure.get("reasons", [])))
        else:
            measure = {"ok": False, "metrics": {}, "reasons": ["no_capture"]}
            verify_ok = False
            print("Verify: FAIL no capture")
        timings["verify_s"] = round(time.monotonic() - t0, 3)

    _write_json(run_paths.measure, measure)

    if not verify_ok:
        result["failed_step"] = "verify"
        result["error_summary"] = "verify failed"
        _triage("verify", pre_info)
        _write_json(run_paths.result, result)
        meta["ended_at"] = datetime.now().isoformat()
        _write_json(run_paths.meta, meta)
        return 6

    timings["total_s"] = round(time.monotonic() - run_started_mono, 3)

    artifacts_copied = _copy_artifacts(firmware_path, run_paths.artifacts_dir)

    print("PASS: Blink verified")
    print(
        "Summary: "
        f"preflight={timings.get('preflight_s', 0)}s "
        f"build={timings.get('build_s', 0)}s "
        f"flash={timings.get('flash_s', 0)}s "
        f"observe={timings.get('observe_s', 0)}s "
        f"verify={timings.get('verify_s', 0)}s "
        f"total={timings.get('total_s', 0)}s"
    )

    result["ok"] = True
    result["failed_step"] = ""
    result["error_summary"] = ""
    result["artifacts"] = artifacts_copied
    _write_json(run_paths.result, result)

    meta.update(
        {
            "ended_at": datetime.now().isoformat(),
            "timings": timings,
            "firmware": {
                "path": firmware_path,
                "sha256": _file_sha256(firmware_path) if firmware_path else "",
            },
        }
    )
    _write_json(run_paths.meta, meta)

    print(f"Run metadata saved: {run_paths.meta}")
    print(f"Run log saved: {run_paths.build_log}")
    return 0


def run(args):
    return run_pipeline(
        probe_path=args.probe,
        board_arg=args.board,
        test_path=args.test,
        wiring=args.wiring,
        output_mode=args.output_mode,
        skip_flash=args.skip_flash,
    )


def run_cli(probe_path, board_id, test_path, wiring=None, output_mode="normal"):
    return run_pipeline(
        probe_path=probe_path,
        board_arg=board_id,
        test_path=test_path,
        wiring=wiring,
        output_mode=output_mode,
    )


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--probe", required=True)
    run_p.add_argument("--board", required=True)
    run_p.add_argument("--test", required=False, default=os.path.join("tests", "blink_gpio.json"))
    run_p.add_argument("--wiring", required=False)
    run_p.add_argument("--skip-flash", action="store_true")
    out_group = run_p.add_mutually_exclusive_group()
    out_group.add_argument("--quiet", action="store_true", help="Concise console output")
    out_group.add_argument("--verbose", action="store_true", help="Verbose console output")

    args = parser.parse_args()
    if args.cmd == "run":
        if args.verbose:
            args.output_mode = "verbose"
        elif args.quiet:
            args.output_mode = "quiet"
        else:
            args.output_mode = "normal"
        code = run(args)
        sys.exit(code)


if __name__ == "__main__":
    main()
