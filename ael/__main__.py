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
from pathlib import Path

from orchestrator import run_cli, run_pipeline, _simple_yaml_load, _normalize_probe_cfg
from ael import assets
from ael import run_manager


def main():
    parser = argparse.ArgumentParser(prog="ael")
    # Follow docs/AI_USAGE_RULES.md: CLI is a deterministic control interface for AI agents.
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--test", required=False)
    run_p.add_argument("--pack", required=False)
    run_p.add_argument("--board", required=False, help="Board id (e.g. rp2040_pico)")
    run_p.add_argument("--dut", required=False, help="DUT id from assets_golden/assets_user")
    run_p.add_argument("--probe", default=os.path.join("configs", "esp32jtag.yaml"))
    run_p.add_argument("--wiring", required=False)
    run_p.add_argument("--bench", required=False, help="Bench id (placeholder, not used)")
    out_group = run_p.add_mutually_exclusive_group()
    out_group.add_argument("--quiet", action="store_true", help="Concise console output")
    out_group.add_argument("--verbose", action="store_true", help="Verbose console output")

    doc_p = sub.add_parser("doctor")
    doc_p.add_argument("--probe", default=os.path.join("configs", "esp32jtag.yaml"))
    doc_p.add_argument("--board", default=os.path.join("configs", "boards", "rp2040_pico.yaml"))
    doc_p.add_argument("--test", default=os.path.join("tests", "blink_gpio.json"))

    pack_p = sub.add_parser("pack")
    pack_p.add_argument("--pack", required=False)
    pack_p.add_argument("--board", required=False)
    pack_p.add_argument("--dut", required=False)
    pack_p.add_argument("--bench", required=False, help="Bench id (placeholder, not used)")
    pack_p.add_argument("--stop-on-fail", action="store_true")
    pack_p.add_argument("--no-flash", action="store_true")
    pack_p.add_argument("--no-build", action="store_true")
    pack_p.add_argument("--verify-only", action="store_true")

    instr_p = sub.add_parser("instruments")
    instr_sub = instr_p.add_subparsers(dest="instr_cmd", required=True)
    instr_list = instr_sub.add_parser("list")
    instr_show = instr_sub.add_parser("show")
    instr_show.add_argument("id")
    instr_find = instr_sub.add_parser("find")
    instr_find.add_argument("--cap", required=True)

    dut_p = sub.add_parser("dut")
    dut_sub = dut_p.add_subparsers(dest="dut_cmd", required=True)
    dut_create = dut_sub.add_parser("create")
    dut_create.add_argument("--from-golden", required=True)
    dut_create.add_argument("--to", required=True)
    dut_promote = dut_sub.add_parser("promote")
    dut_promote.add_argument("--id", required=True)
    dut_promote.add_argument("--as", dest="as_id", required=False)
    dut_promote.add_argument("--delete-source", action="store_true")

    args = parser.parse_args()
    repo_root = os.path.dirname(os.path.dirname(__file__))
    probe_default = os.path.join("configs", "esp32jtag.yaml")
    notify_probe = os.path.join("configs", "esp32jtag_notify.yaml")
    if args.cmd == "run":
        if args.verbose:
            output_mode = "verbose"
        elif args.quiet:
            output_mode = "quiet"
        else:
            output_mode = "normal"
        board_id = args.board
        test_path = args.test
        pack_path = args.pack
        probe_path = args.probe
        probe_provided = "--probe" in sys.argv
        if args.dut:
            dut = assets.load_dut_prefer_user(args.dut)
            if not dut:
                print(f"DUT not found: {args.dut}")
                sys.exit(2)
            dut_path = Path(dut["path"])
            manifest = dut.get("manifest") if isinstance(dut, dict) else {}
            if not board_id:
                candidate = Path("configs") / "boards" / f"{args.dut}.yaml"
                if candidate.exists():
                    board_id = args.dut
            if test_path and not os.path.isabs(test_path):
                dut_test = dut_path / "tests" / test_path
                if dut_test.exists():
                    test_path = str(dut_test)
            if pack_path and not os.path.isabs(pack_path):
                dut_pack = dut_path / "packs" / pack_path
                if dut_pack.exists():
                    pack_path = str(dut_pack)
            if not test_path and not pack_path:
                default_packs = []
                if isinstance(manifest, dict):
                    default_packs = manifest.get("default_packs", []) or []
                if default_packs:
                    pack_path = default_packs[0]
                else:
                    dut_packs_dir = dut_path / "packs"
                    if dut_packs_dir.exists():
                        packs = sorted([p for p in dut_packs_dir.glob("*.json")])
                        if packs:
                            pack_path = str(packs[0])
                    dut_tests_dir = dut_path / "tests"
                    if not pack_path and dut_tests_dir.exists():
                        tests = sorted([t for t in dut_tests_dir.glob("*.json")])
                        if tests:
                            test_path = str(tests[0])
            if not test_path and not pack_path:
                print("DUT has no tests or packs. Provide --test or --pack.")
                sys.exit(2)
            if pack_path:
                code = run_pack(
                    pack_path=pack_path,
                    board_override=board_id,
                    stop_on_fail=False,
                    no_flash=False,
                    no_build=False,
                    verify_only=False,
                )
                sys.exit(code)
        if not probe_provided and not probe_path:
            probe_path = probe_default
        if not probe_provided:
            notify_full = os.path.join(repo_root, notify_probe)
            if (board_id == "esp32s3_devkit" or args.dut == "esp32s3_devkit") and os.path.exists(
                notify_full
            ):
                probe_path = notify_probe
        if not test_path and not pack_path:
            print("Provide --test or --pack (or use --dut with defaults).")
            sys.exit(2)
        code = run_cli(
            probe_path=probe_path,
            board_id=board_id,
            test_path=test_path,
            wiring=args.wiring,
            output_mode=output_mode,
        )
        sys.exit(code)
    if args.cmd == "doctor":
        code = run_doctor(args.probe, args.board, args.test)
        sys.exit(code)
    if args.cmd == "instruments":
        from ael.instruments.registry import InstrumentRegistry

        registry = InstrumentRegistry()
        if args.instr_cmd == "list":
            print(json.dumps(registry.list(), indent=2, sort_keys=True))
            sys.exit(0)
        if args.instr_cmd == "show":
            inst = registry.get(args.id)
            if not inst:
                print(f"Instrument not found: {args.id}")
                sys.exit(2)
            print(json.dumps(inst, indent=2, sort_keys=True))
            sys.exit(0)
        if args.instr_cmd == "find":
            matches = registry.find_by_capability(args.cap)
            print(json.dumps(matches, indent=2, sort_keys=True))
            sys.exit(0)
    if args.cmd == "pack":
        board_override = args.board
        if args.dut:
            dut = assets.load_dut_prefer_user(args.dut)
            if not dut:
                print(f"DUT not found: {args.dut}")
                sys.exit(2)
            if not board_override:
                candidate = Path("configs") / "boards" / f"{args.dut}.yaml"
                if candidate.exists():
                    board_override = args.dut
            if args.pack and not os.path.isabs(args.pack):
                dut_pack = Path(dut["path"]) / "packs" / args.pack
                if dut_pack.exists():
                    args.pack = str(dut_pack)
            if not args.pack:
                manifest = dut.get("manifest") if isinstance(dut, dict) else {}
                default_packs = manifest.get("default_packs", []) if isinstance(manifest, dict) else []
                if default_packs:
                    args.pack = default_packs[0]
                else:
                    dut_packs_dir = Path(dut["path"]) / "packs"
                    if dut_packs_dir.exists():
                        packs = sorted([p for p in dut_packs_dir.glob("*.json")])
                        if packs:
                            args.pack = str(packs[0])
            if not args.pack:
                print("DUT has no packs. Provide --pack.")
                sys.exit(2)
        code = run_pack(
            pack_path=args.pack,
            board_override=board_override,
            stop_on_fail=args.stop_on_fail,
            no_flash=args.no_flash,
            no_build=args.no_build,
            verify_only=args.verify_only,
        )
        sys.exit(code)
    if args.cmd == "dut":
        if args.dut_cmd == "create":
            code = dut_create_cmd(args.from_golden, args.to)
            sys.exit(code)
        if args.dut_cmd == "promote":
            code = dut_promote_cmd(args.id, args.as_id, args.delete_source)
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


def _update_manifest_id(manifest, new_id, verified_status=None):
    if not isinstance(manifest, dict):
        manifest = {}
    manifest["id"] = new_id
    if verified_status is not None:
        verified = manifest.get("verified") if isinstance(manifest.get("verified"), dict) else {}
        verified["status"] = bool(verified_status)
        manifest["verified"] = verified
    return manifest


def dut_create_cmd(from_golden_id, to_user_id):
    src = Path("assets_golden") / "duts" / from_golden_id
    dst = Path("assets_user") / "duts" / to_user_id
    if not src.exists():
        print(f"DUT create: golden id not found: {from_golden_id}")
        return 1
    if dst.exists():
        print(f"DUT create: destination already exists: {dst}")
        return 2
    assets.copy_dut_skeleton(src, dst)
    manifest_path = dst / "manifest.yaml"
    manifest = assets._load_yaml(manifest_path) if manifest_path.exists() else {}
    manifest = _update_manifest_id(manifest, to_user_id, verified_status=False)
    assets.save_manifest(manifest_path, manifest)
    notes_path = dst / "notes.md"
    if not notes_path.exists():
        notes_path.write_text(f"Created from golden {from_golden_id}\n", encoding="utf-8")
    print(f"DUT create: {dst}")
    return 0


def dut_promote_cmd(user_id, as_id=None, delete_source=False):
    src = Path("assets_user") / "duts" / user_id
    if not src.exists():
        print(f"DUT promote: user id not found: {user_id}")
        return 1
    manifest_path = src / "manifest.yaml"
    if not manifest_path.exists():
        print("DUT promote: manifest.yaml missing")
        return 2
    manifest = assets._load_yaml(manifest_path)
    missing = assets._validate_manifest(manifest)
    if missing:
        print("DUT promote: manifest missing fields: " + ", ".join(missing))
        return 3
    golden_id = as_id or user_id
    dst = Path("assets_golden") / "duts" / golden_id
    if dst.exists():
        print(f"DUT promote: destination already exists: {dst}")
        return 4
    assets.copy_dut_skeleton(src, dst)
    dst_manifest_path = dst / "manifest.yaml"
    verified_status = manifest.get("verified", {}).get("status", False) if isinstance(manifest, dict) else False
    manifest = _update_manifest_id(manifest, golden_id, verified_status=verified_status)
    assets.save_manifest(dst_manifest_path, manifest)
    promo_note = dst / "PROMOTION.md"
    promo_note.write_text(f"Promoted from user DUT {user_id}.\n", encoding="utf-8")
    if delete_source:
        shutil.rmtree(src)
    print(f"DUT promote: {dst}")
    return 0


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
    notify_probe = os.path.join("configs", "esp32jtag_notify.yaml")
    default_probe = os.path.join(repo_root, "configs", "esp32jtag.yaml")
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
            probe_path=(
                os.path.join(repo_root, notify_probe)
                if pack_board == "esp32s3_devkit" and os.path.exists(os.path.join(repo_root, notify_probe))
                else default_probe
            ),
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
            f"<li>{r['test']} — {'OK' if r['ok'] else 'FAIL'} — "
            f"<a href=\"file://{run_dir}\">{run_dir}</a></li>"
        )
    report.extend(["</ul>", "</body></html>"])
    with open(os.path.join(pack_root, "pack_report.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    main()
