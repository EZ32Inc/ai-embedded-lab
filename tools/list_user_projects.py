#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def _simple_yaml_load(path: Path) -> dict:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def main() -> int:
    p = argparse.ArgumentParser(description="List lightweight AEL user projects.")
    p.add_argument("--projects-root", default="projects")
    args = p.parse_args()

    root = Path(args.projects_root)
    if not root.exists():
        print("project_count: 0")
        return 0

    projects = []
    for project_yaml in sorted(root.glob("*/project.yaml")):
        payload = _simple_yaml_load(project_yaml)
        if not payload:
            continue
        projects.append(
            {
                "project_id": str(payload.get("project_id", "")).strip(),
                "project_name": str(payload.get("project_name", "")).strip(),
                "project_user": str(payload.get("project_user", "")).strip(),
                "status": str(payload.get("status", "")).strip(),
                "target_mcu": str(payload.get("target_mcu", "")).strip(),
                "closest_mature_ael_path": str(payload.get("closest_mature_ael_path", "")).strip(),
            }
        )

    print(f"project_count: {len(projects)}")
    for item in projects:
        print(f"- {item['project_id']}")
        print(f"  - name: {item['project_name']}")
        print(f"  - user: {item['project_user']}")
        print(f"  - status: {item['status']}")
        print(f"  - target_mcu: {item['target_mcu']}")
        print(f"  - mature_path: {item['closest_mature_ael_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
