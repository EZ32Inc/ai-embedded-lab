import argparse
import json
import os
import sys
from datetime import datetime

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


def run(args):
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

    if not preflight.run(probe_cfg):
        return 2
    print("SWD and network connection verified. Starting task.")

    firmware_path = build_cmake.run(board_cfg)
    if not firmware_path:
        return 3

    if not args.skip_flash:
        if not flash_bmda_gdbmi.run(probe_cfg, firmware_path):
            return 4
    else:
        print("Flash: SKIPPED (user will flash via UF2)")

    test_path = os.path.join(os.path.dirname(__file__), "tests", "blink_gpio.json")
    with open(test_path, "r", encoding="utf-8") as f:
        test = json.load(f)

    ok = observe_gpio_pin.run(
        probe_cfg,
        pin=wiring.get("verify"),
        duration_s=float(test.get("duration_s", 3.0)),
        expected_hz=float(test.get("expected_hz", 1.0)),
        min_edges=int(test.get("min_edges", 2)),
        max_edges=int(test.get("max_edges", 6)),
    )
    if not ok:
        return 5

    print("PASS: Blink verified")
    return 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--probe", required=True)
    run_p.add_argument("--board", required=True)
    run_p.add_argument("--wiring", required=False)
    run_p.add_argument("--skip-flash", action="store_true")

    args = parser.parse_args()
    if args.cmd == "run":
        code = run(args)
        sys.exit(code)


if __name__ == "__main__":
    main()
