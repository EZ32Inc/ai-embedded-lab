import argparse
import json
import os
import sys
from datetime import datetime
import hashlib
import time

from adapters import preflight, build_cmake, flash_bmda_gdbmi, observe_gpio_pin


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
                value = value.strip().strip("\"")
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


class _Tee:
    def __init__(self, file_obj, console, mode):
        self._file = file_obj
        self._console = console
        self._mode = mode
        self._buf = ""

    def write(self, s):
        if not s:
            return 0
        self._file.write(s)
        self._file.flush()
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self._write_console_line(line + "\n")
        return len(s)

    def flush(self):
        if self._buf:
            self._write_console_line(self._buf)
            self._buf = ""
        self._file.flush()
        if hasattr(self._console, "flush"):
            self._console.flush()

    def _write_console_line(self, line):
        if self._mode == "verbose":
            self._console.write(line)
            return
        if self._mode == "quiet":
            prefixes = (
                "AI:",
                "Using ",
                "Wiring:",
                "Preflight:",
                "SWD ",
                "Build:",
                "Flash:",
                "Verify:",
                "PASS:",
                "FAIL:",
                "Summary:",
                "Run metadata saved:",
                "Run log saved:",
                "Hint:",
            )
            if line.startswith(prefixes):
                self._console.write(line)
            return
        # normal mode: drop very noisy build lines, keep status
        noisy = (
            "gmake",
            "/usr/bin/cmake",
            "Scanning dependencies",
            "Dependee ",
            "Dependencies file",
            "Consolidate compiler generated dependencies",
            "Built target",
            "Entering directory",
            "Leaving directory",
        )
        if line.startswith(noisy):
            return
        self._console.write(line)


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit():
    try:
        import subprocess

        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            return (res.stdout or "").strip()
    except Exception:
        pass
    return ""


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


def run(args):
    run_started = datetime.now()
    run_started_mono = time.monotonic()
    run_id = run_started.strftime("%Y%m%d_%H%M%S")
    progress_dir = os.path.join(os.path.dirname(__file__), "progress")
    os.makedirs(progress_dir, exist_ok=True)
    meta_path = os.path.join(progress_dir, f"run_{run_id}.json")
    log_path = os.path.join(progress_dir, f"run_{run_id}.log")

    with open(log_path, "w", encoding="utf-8") as logf:
        orig_out = sys.stdout
        orig_err = sys.stderr
        sys.stdout = _Tee(logf, orig_out, args.output_mode)
        sys.stderr = _Tee(logf, orig_err, args.output_mode)
        code = 0
        try:
            code = _run_pipeline(args, run_started, run_started_mono, run_id, meta_path, log_path)
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            sys.stdout = orig_out
            sys.stderr = orig_err
    return code


def _run_pipeline(args, run_started, run_started_mono, run_id, meta_path, log_path):
    status = {"stage": "init", "ok": False}

    probe_raw = _simple_yaml_load(args.probe)
    probe_cfg = _normalize_probe_cfg(probe_raw)
    board_cfg = _simple_yaml_load(args.board).get("board", {})

    wiring_overrides = _parse_wiring(args.wiring or "")
    wiring = _merge_wiring(board_cfg.get("default_wiring", {}), wiring_overrides)
    wiring = _require_wiring(wiring, ["swd", "reset", "verify"])

    print("AI: starting pipeline")
    print(f"Using probe: {probe_cfg.get('name', 'unknown')} @ {probe_cfg.get('ip', 'unknown')}:{probe_cfg.get('gdb_port', 'unknown')}")
    print(f"Using board: {board_cfg.get('name', 'unknown')} target={board_cfg.get('target', 'unknown')}")
    print(f"Wiring: swd={wiring.get('swd')} reset={wiring.get('reset')} verify={wiring.get('verify')}")

    timings = {}

    t0 = time.monotonic()
    ok_pre, pre_info = preflight.run(probe_cfg)
    timings["preflight_s"] = round(time.monotonic() - t0, 3)
    if not ok_pre:
        status = {"stage": "preflight", "ok": False}
        _write_meta(meta_path, run_started, status, probe_cfg, board_cfg, wiring, timings, pre_info, "")
        _triage("preflight", pre_info)
        print(f"Run log saved: {log_path}")
        return 2
    print("SWD and network connection verified. Starting task.")
    if not pre_info.get("targets"):
        print("Preflight: warning - no targets reported by probe.")

    t0 = time.monotonic()
    firmware_path = build_cmake.run(board_cfg)
    timings["build_s"] = round(time.monotonic() - t0, 3)
    if not firmware_path:
        status = {"stage": "build", "ok": False}
        _write_meta(meta_path, run_started, status, probe_cfg, board_cfg, wiring, timings, pre_info, "")
        _triage("build", pre_info)
        print(f"Run log saved: {log_path}")
        return 3

    if not args.skip_flash:
        t0 = time.monotonic()
        flash_ok = flash_bmda_gdbmi.run(probe_cfg, firmware_path)
        timings["flash_s"] = round(time.monotonic() - t0, 3)
        if not flash_ok:
            status = {"stage": "flash", "ok": False}
            _write_meta(meta_path, run_started, status, probe_cfg, board_cfg, wiring, timings, pre_info, firmware_path)
            _triage("flash", pre_info)
            print(f"Run log saved: {log_path}")
            return 4
    else:
        print("Flash: SKIPPED (user will flash via UF2)")

    test_path = os.path.join(os.path.dirname(__file__), "tests", "blink_gpio.json")
    with open(test_path, "r", encoding="utf-8") as f:
        test = json.load(f)

    t0 = time.monotonic()
    ok = observe_gpio_pin.run(
        probe_cfg,
        pin=wiring.get("verify"),
        duration_s=float(test.get("duration_s", 3.0)),
        expected_hz=float(test.get("expected_hz", 1.0)),
        min_edges=int(test.get("min_edges", 2)),
        max_edges=int(test.get("max_edges", 6)),
    )
    timings["verify_s"] = round(time.monotonic() - t0, 3)
    if not ok:
        status = {"stage": "verify", "ok": False}
        _write_meta(meta_path, run_started, status, probe_cfg, board_cfg, wiring, timings, pre_info, firmware_path)
        _triage("verify", pre_info)
        print(f"Run log saved: {log_path}")
        return 5

    total_s = round(time.monotonic() - run_started_mono, 3)
    timings["total_s"] = total_s

    print("PASS: Blink verified")
    print(
        "Summary: "
        f"preflight={timings.get('preflight_s', 0)}s "
        f"build={timings.get('build_s', 0)}s "
        f"flash={timings.get('flash_s', 0)}s "
        f"verify={timings.get('verify_s', 0)}s "
        f"total={timings.get('total_s', 0)}s"
    )

    status = {"stage": "complete", "ok": True}
    _write_meta(meta_path, run_started, status, probe_cfg, board_cfg, wiring, timings, pre_info, firmware_path)
    print(f"Run metadata saved: {meta_path}")
    print(f"Run log saved: {log_path}")
    return 0


def _write_meta(path, started, status, probe_cfg, board_cfg, wiring, timings, pre_info, firmware_path):
    meta = {
        "run_id": started.strftime("%Y%m%d_%H%M%S"),
        "started_at": started.isoformat(),
        "status": status,
        "probe": {
            "name": probe_cfg.get("name"),
            "ip": probe_cfg.get("ip"),
            "gdb_port": probe_cfg.get("gdb_port"),
            "gdb_cmd": probe_cfg.get("gdb_cmd"),
        },
        "board": {
            "name": board_cfg.get("name"),
            "target": board_cfg.get("target"),
        },
        "wiring": wiring,
        "preflight": pre_info,
        "timings": timings,
        "firmware": {
            "path": firmware_path,
            "sha256": _file_sha256(firmware_path) if firmware_path else "",
        },
        "git_commit": _git_commit(),
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, sort_keys=True)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--probe", required=True)
    run_p.add_argument("--board", required=True)
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
