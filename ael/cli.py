from __future__ import annotations

import argparse
import json
from datetime import datetime
from urllib import request
from urllib.error import HTTPError, URLError


def _generated_task_id() -> str:
    return f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def submit_task(
    plan_file: str,
    api_url: str = "http://127.0.0.1:8765/v1/tasks",
    task_id: str | None = None,
    description: str = "",
    priority: str = "normal",
    created_by: str = "ael-submit",
) -> tuple[int, dict]:
    payload = {
        "task_id": task_id or _generated_task_id(),
        "description": description,
        "plan_file": str(plan_file),
        "priority": str(priority),
        "created_by": str(created_by),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=api_url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            out = json.loads(body) if body else {}
            return int(resp.status), out if isinstance(out, dict) else {}
    except HTTPError as exc:
        try:
            err = json.loads((exc.read() or b"{}").decode("utf-8"))
        except Exception:
            err = {"ok": False, "error": str(exc)}
        return int(exc.code), err if isinstance(err, dict) else {"ok": False, "error": str(exc)}
    except URLError as exc:
        return 0, {"ok": False, "error": f"connection failed: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(prog="ael.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    submit_p = sub.add_parser("submit")
    submit_p.add_argument("plan_file")
    submit_p.add_argument("--api", default="http://127.0.0.1:8765/v1/tasks")
    submit_p.add_argument("--task-id", default=None)
    submit_p.add_argument("--description", default="")
    submit_p.add_argument("--priority", default="normal")
    submit_p.add_argument("--created-by", default="ael-submit")

    args = parser.parse_args()
    if args.cmd == "submit":
        status, payload = submit_task(
            plan_file=args.plan_file,
            api_url=args.api,
            task_id=args.task_id,
            description=args.description,
            priority=args.priority,
            created_by=args.created_by,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        if status == 200 and bool(payload.get("accepted")):
            return 0
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
