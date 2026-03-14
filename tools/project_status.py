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


def _fmt_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(v).strip() for v in values if str(v).strip()]


def main() -> int:
    p = argparse.ArgumentParser(description="Show lightweight status for an AEL user project shell.")
    p.add_argument("project_dir")
    args = p.parse_args()

    project_dir = Path(args.project_dir)
    payload = _simple_yaml_load(project_dir / "project.yaml")
    if not payload:
        raise SystemExit(f"missing or unreadable project metadata: {project_dir / 'project.yaml'}")

    print(f"project_id: {payload.get('project_id', '')}")
    print(f"project_name: {payload.get('project_name', '')}")
    print(f"domain: {payload.get('domain', '')}")
    print(f"status: {payload.get('status', '')}")
    print(f"target_mcu: {payload.get('target_mcu', '')}")
    print(f"closest_mature_ael_path: {payload.get('closest_mature_ael_path', '')}")
    print(f"next_recommended_action: {payload.get('next_recommended_action', '')}")

    confirmed = _fmt_list(payload.get("confirmed_facts"))
    assumptions = _fmt_list(payload.get("assumptions"))
    unresolved = _fmt_list(payload.get("unresolved_items"))
    system_refs = _fmt_list(payload.get("system_refs"))

    if confirmed:
        print("confirmed_facts:")
        for item in confirmed:
            print(f"  - {item}")
    if assumptions:
        print("assumptions:")
        for item in assumptions:
            print(f"  - {item}")
    if unresolved:
        print("unresolved_items:")
        for item in unresolved:
            print(f"  - {item}")
    if system_refs:
        print("system_refs:")
        for item in system_refs:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
