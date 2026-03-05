import argparse
import os
import sys
import json
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from ael.orchestrator import run_cli, run_pipeline, _simple_yaml_load, _normalize_probe_cfg
from ael import assets
from ael.bridge_server import run_server as run_bridge_server
from ael.doctor_checks import la_capture_ok, monitor_version, validate_config
from ael.nightly import NightlyConfig, run_nightly
from ael.submit import submit_to_bridge
from ael import run_manager
from ael.config_resolver import (
    resolve_board_config,
    resolve_doctor_required_tools,
    resolve_probe_config,
)


def _run_agent_loop(queue: str, report_root: str, poll: float) -> None:
    from ael.agent import _AgentMode, run_sweep

    mode = _AgentMode(branch_worker=False, push=False, remote="origin", gates_path=None)
    while True:
        run_sweep(queue_path=queue, mode=mode, report_root=report_root, max_tasks=None, verbose=False)
        time.sleep(max(0.1, float(poll)))


def run_up(host: str, port: int, queue: str, report_root: str, poll: float) -> int:
    print("AEL system starting...")

    bridge_thread = threading.Thread(
        target=run_bridge_server,
        kwargs={"host": str(host), "port": int(port), "queue_root": str(queue)},
        daemon=True,
    )
    agent_thread = threading.Thread(
        target=_run_agent_loop,
        kwargs={"queue": str(queue), "report_root": str(report_root), "poll": float(poll)},
        daemon=True,
    )
    bridge_thread.start()
    agent_thread.start()

    print(f"Bridge running at http://{host}:{int(port)}")
    print("Agent queue runner active")
    print("System ready.")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("AEL system stopping...")
        return 0


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _task_line(path: Path) -> str:
    payload = _load_json(path)
    task_id = str(payload.get("task_id", path.stem)).strip() or path.stem
    title = str(payload.get("title", "")).strip() or path.name
    state = path.parent.name
    return f"{task_id} {title} ({state})"


def run_status(queue: str) -> int:
    qroot = Path(queue)
    running = sorted([p for p in (qroot / "running").glob("*.json") if not p.name.endswith(".state.json")])
    done = sorted([p for p in (qroot / "done").glob("*.json") if not p.name.endswith(".state.json")])

    print("RUNNING TASKS")
    print("-------------")
    if running:
        for p in running:
            print(_task_line(p))
    else:
        print("(none)")

    print("")
    print("COMPLETED")
    print("---------")
    if done:
        for p in done[-20:]:
            print(_task_line(p))
    else:
        print("(none)")
    return 0


def main():
    parser = argparse.ArgumentParser(prog="ael")
    # Follow docs/AI_USAGE_RULES.md: CLI is a deterministic control interface for AI agents.
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--test", required=False)
    run_p.add_argument("--pack", required=False)
    run_p.add_argument("--board", required=False, help="Board id")
    run_p.add_argument("--dut", required=False, help="DUT id from assets_golden/assets_user")
    run_p.add_argument("--probe", required=False, default=None)
    run_p.add_argument("--wiring", required=False)
    run_p.add_argument("--bench", required=False, help="Bench id (placeholder, not used)")
    out_group = run_p.add_mutually_exclusive_group()
    out_group.add_argument("--quiet", action="store_true", help="Concise console output")
    out_group.add_argument("--verbose", action="store_true", help="Verbose console output")

    doc_p = sub.add_parser("doctor")
    doc_p.add_argument("--probe", default=None)
    doc_p.add_argument("--board", default=None)
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

    submit_p = sub.add_parser("submit")
    submit_p.add_argument("input_text", help="Natural language prompt or JSON payload/path when --json is set")
    submit_p.add_argument("--api", default="http://127.0.0.1:8844/v1/tasks")
    submit_p.add_argument("--json", action="store_true", help="Treat input_text as JSON object or JSON file path")

    bridge_p = sub.add_parser("bridge")
    bridge_p.add_argument("--host", default=os.environ.get("AEL_BRIDGE_HOST", "127.0.0.1"))
    bridge_p.add_argument("--port", type=int, default=int(os.environ.get("AEL_BRIDGE_PORT", "8844")))
    bridge_p.add_argument("--queue", default=os.environ.get("AEL_QUEUE_ROOT", "queue"))

    up_p = sub.add_parser("up")
    up_p.add_argument("--host", default=os.environ.get("AEL_BRIDGE_HOST", "127.0.0.1"))
    up_p.add_argument("--port", type=int, default=int(os.environ.get("AEL_BRIDGE_PORT", "8844")))
    up_p.add_argument("--queue", default=os.environ.get("AEL_QUEUE_ROOT", "queue"))
    up_p.add_argument(
        "--report-root",
        default=os.environ.get("AEL_REPORT_ROOT") or str(Path(__file__).resolve().parents[1] / "reports"),
    )
    up_p.add_argument("--poll", type=float, default=0.5, help="Agent queue poll interval in seconds")

    status_p = sub.add_parser("status")
    status_p.add_argument("--queue", default=os.environ.get("AEL_QUEUE_ROOT", "queue"))

    nightly_p = sub.add_parser("nightly")
    nightly_p.add_argument("--max-plans", type=int, default=3)
    nightly_p.add_argument("--allow-on-master", action="store_true")
    nightly_p.add_argument("--no-stash", action="store_true")
    nightly_p.add_argument("--dry-run", action="store_true")
    nightly_p.add_argument("--verbose", action="store_true")
    nightly_p.add_argument("--once", action="store_true", help="Alias; nightly runs once by default.")
    nightly_p.add_argument("--queue", default=os.environ.get("AEL_QUEUE_ROOT", "queue"))
    nightly_p.add_argument(
        "--report-root",
        default=os.environ.get("AEL_REPORT_ROOT") or str(Path(__file__).resolve().parents[1] / "reports"),
    )

    args = parser.parse_args()
    repo_root = os.path.dirname(os.path.dirname(__file__))
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
        probe_path = resolve_probe_config(repo_root, args, board_id=board_id)
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
        doc_probe = resolve_probe_config(repo_root, args, pack_meta={"mode": "doctor"})
        doc_board = resolve_board_config(repo_root, args, pack_meta={"mode": "doctor"})
        code = run_doctor(doc_probe, doc_board, args.test)
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
    if args.cmd == "submit":
        status, payload = submit_to_bridge(
            user_input=args.input_text,
            api_url=args.api,
            json_mode=bool(args.json),
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        if status == 200 and bool(payload.get("ok", False)):
            task_id = str(payload.get("task_id", "")).strip()
            print("Task submitted")
            if task_id:
                print(f"task_id: {task_id}")
            sys.exit(0)
        sys.exit(1)
    if args.cmd == "bridge":
        sys.exit(run_bridge_server(host=str(args.host), port=int(args.port), queue_root=str(args.queue)))
    if args.cmd == "up":
        sys.exit(
            run_up(
                host=str(args.host),
                port=int(args.port),
                queue=str(args.queue),
                report_root=str(args.report_root),
                poll=float(args.poll),
            )
        )
    if args.cmd == "status":
        sys.exit(run_status(queue=str(args.queue)))
    if args.cmd == "nightly":
        cfg = NightlyConfig(
            date_str=datetime.now().strftime("%Y-%m-%d"),
            max_plans=int(args.max_plans),
            allow_on_master=bool(args.allow_on_master),
            stash_dirty=not bool(args.no_stash),
            work_branch_prefix="agent",
            backlog_sources=[str(Path(args.queue) / "inbox")],
            dry_run=bool(args.dry_run),
            verbose=bool(args.verbose),
            queue_path=str(args.queue),
            report_root=str(args.report_root),
        )
        print("Nightly run starting...")
        summary = run_nightly(cfg)
        print(f"Nightly report: {summary.get('report_path', '')}")
        for item in summary.get("plans", []):
            status = str(item.get("status", ""))
            branch = str(item.get("branch", ""))
            commit = str(item.get("commit", ""))
            title = str(item.get("title", ""))
            print(f"[{status}] {title} | branch={branch} | commit={commit or '-'}")
        print("Nightly overall: " + ("OK" if bool(summary.get("ok", False)) else "FAILED"))
        sys.exit(0 if bool(summary.get("ok", False)) else 1)


def _check_tools(tools):
    missing = [t for t in tools if shutil.which(t) is None]
    return missing


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
            missing = _check_tools(list(resolve_doctor_required_tools()))
            if missing:
                print("Doctor: missing tools: " + ", ".join(missing))
            else:
                print("Doctor: tools OK")

            ok_bmp, bmp_info = monitor_version(probe_cfg)
            print("Doctor: BMP monitor -> " + ("OK" if ok_bmp else "FAIL"))
            if bmp_info:
                print(bmp_info)

            ok_la, la_info = la_capture_ok(probe_cfg)
            print("Doctor: LA capture -> " + ("OK" if ok_la else "FAIL"))
            if la_info:
                print(la_info)

            issues = validate_config(probe_raw, board_raw, test_raw)
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
        print(f"Using pack: {pack_name}")
        print(f"Pack test: {t}")
        probe_path = resolve_probe_config(
            repo_root,
            args=None,
            board_id=pack_board,
            pack_meta={"mode": "pack", "board": pack_board, "absolute_paths": True},
        )
        code, run_paths = run_pipeline(
            probe_path=probe_path,
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
