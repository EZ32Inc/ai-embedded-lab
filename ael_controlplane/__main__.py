from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from ael import paths as ael_paths
from ael_controlplane.agent import _AgentMode, run_sweep
from ael_controlplane.bridge_server import run_server as run_bridge_server
from ael_controlplane.nightly import NightlyConfig, run_nightly
from ael_controlplane.submit import submit_to_bridge


def _run_agent_loop(queue: str, report_root: str, poll: float) -> None:
    mode = _AgentMode(branch_worker=False, push=False, remote="origin", gates_path=None)
    while True:
        run_sweep(queue_path=queue, mode=mode, report_root=report_root, max_tasks=None, verbose=False)
        time.sleep(max(0.1, float(poll)))


def run_up(host: str, port: int, queue: str, report_root: str, poll: float) -> int:
    print("AEL control-plane starting...")

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
    print("Control-plane ready.")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("AEL control-plane stopping...")
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


def main() -> int:
    parser = argparse.ArgumentParser(prog="ael_controlplane")
    sub = parser.add_subparsers(dest="cmd", required=True)

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
        default=os.environ.get("AEL_REPORT_ROOT") or str(ael_paths.reports_root()),
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
        default=os.environ.get("AEL_REPORT_ROOT") or str(ael_paths.reports_root()),
    )

    args = parser.parse_args()

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
            return 0
        return 1

    if args.cmd == "bridge":
        return run_bridge_server(host=str(args.host), port=int(args.port), queue_root=str(args.queue))

    if args.cmd == "up":
        return run_up(
            host=str(args.host),
            port=int(args.port),
            queue=str(args.queue),
            report_root=str(args.report_root),
            poll=float(args.poll),
        )

    if args.cmd == "status":
        return run_status(queue=str(args.queue))

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
        return 0 if bool(summary.get("ok", False)) else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
