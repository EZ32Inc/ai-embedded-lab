from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
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


def _yaml_load(path: Path) -> dict:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _fmt_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(v).strip() for v in values if str(v).strip()]


def _cmd_project_list(projects_root: str) -> int:
    root = Path(projects_root)
    if not root.exists():
        print("project_count: 0")
        return 0
    projects = []
    for project_yaml in sorted(root.glob("*/project.yaml")):
        payload = _yaml_load(project_yaml)
        if not payload:
            continue
        projects.append(payload)
    print(f"project_count: {len(projects)}")
    for p in projects:
        print(f"- {p.get('project_id', '')}")
        print(f"  - name: {p.get('project_name', '')}")
        print(f"  - user: {p.get('project_user', '')}")
        print(f"  - status: {p.get('status', '')}")
        print(f"  - target_mcu: {p.get('target_mcu', '')}")
        print(f"  - mature_path: {p.get('closest_mature_ael_path', '')}")
        blocker = str(p.get("current_blocker", "")).strip()
        if blocker:
            print(f"  - current_blocker: {blocker}")
        print(f"  - next_recommended_action: {p.get('next_recommended_action', '')}")
    return 0


def _cmd_project_status(project_id: str, projects_root: str) -> int:
    project_dir = Path(projects_root) / project_id
    payload = _yaml_load(project_dir / "project.yaml")
    if not payload:
        print(f"error: missing or unreadable project metadata: {project_dir / 'project.yaml'}")
        return 1
    print(f"project_id: {payload.get('project_id', '')}")
    print(f"project_name: {payload.get('project_name', '')}")
    print(f"domain: {payload.get('domain', '')}")
    print(f"project_user: {payload.get('project_user', '')}")
    print(f"status: {payload.get('status', '')}")
    print(f"target_mcu: {payload.get('target_mcu', '')}")
    print(f"closest_mature_ael_path: {payload.get('closest_mature_ael_path', '')}")
    blocker = str(payload.get("current_blocker", "")).strip()
    print(f"current_blocker: {blocker or 'none'}")
    print(f"last_action: {payload.get('last_action', '')}")
    print(f"next_recommended_action: {payload.get('next_recommended_action', '')}")
    for label, key in [
        ("confirmed_facts", "confirmed_facts"),
        ("assumptions", "assumptions"),
        ("unresolved_items", "unresolved_items"),
        ("system_refs", "system_refs"),
    ]:
        items = _fmt_list(payload.get(key))
        if items:
            print(f"{label}:")
            for item in items:
                print(f"  - {item}")
    return 0


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

    project_p = sub.add_parser("project", help="user project management")
    project_sub = project_p.add_subparsers(dest="project_cmd", required=True)

    list_p = project_sub.add_parser("list", help="list all user projects")
    list_p.add_argument("--projects-root", default="projects")

    status_p = project_sub.add_parser("status", help="show status of one user project")
    status_p.add_argument("project_id")
    status_p.add_argument("--projects-root", default="projects")

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

    if args.cmd == "project":
        if args.project_cmd == "list":
            return _cmd_project_list(args.projects_root)
        if args.project_cmd == "status":
            return _cmd_project_status(args.project_id, args.projects_root)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
