#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def _slugify(value: str) -> str:
    text = value.strip().lower().replace(" ", "_").replace("-", "_")
    out = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            out.append(ch)
    slug = "".join(out).strip("_")
    return slug or "user_project"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Create a lightweight AEL user-project shell.")
    p.add_argument("--project-id", required=True)
    p.add_argument("--project-name", required=True)
    p.add_argument("--user-goal", required=True)
    p.add_argument("--target-mcu", required=True)
    p.add_argument("--mature-path", required=True)
    p.add_argument("--project-user", default="local_user")
    p.add_argument("--confirmed-fact", default="")
    p.add_argument("--assumption", default="")
    p.add_argument("--unresolved-item", action="append", default=[])
    p.add_argument("--system-ref", action="append", default=[])
    p.add_argument("--cross-domain-reason", default="")
    p.add_argument("--tool-branch", default="")
    p.add_argument("--system-change-status", default="integrated")
    p.add_argument("--output-root", default="projects")
    args = p.parse_args()

    project_id = _slugify(args.project_id)
    project_dir = Path(args.output_root) / project_id
    if project_dir.exists():
        raise SystemExit(f"project already exists: {project_dir}")

    unresolved = list(args.unresolved_item or [])
    while len(unresolved) < 2:
        unresolved.append("Needs clarification")

    confirmed_fact = args.confirmed_fact or f"User requested a project for {args.target_mcu}"
    assumption = args.assumption or (
        f"The user's board is close enough to the current mature {args.mature_path} path to begin from a shell-first workflow"
    )
    next_action = "clarify setup, wiring, validation approach, and desired first example"
    system_refs = list(args.system_ref or [])
    while len(system_refs) < 2:
        system_refs.append("")
    cross_domain_reason = args.cross_domain_reason or (
        f"project is anchored to the current mature {args.mature_path} capability path"
    )

    project_yaml = f"""project_id: {project_id}
project_name: {args.project_name}
project_type: user_project
domain: user_project_domain
project_user: {args.project_user}
user_goal: {args.user_goal}
target_mcu: {args.target_mcu}
closest_mature_ael_path: {args.mature_path}
system_refs:
  - {system_refs[0]}
  - {system_refs[1]}
cross_domain_links:
  - type: mature_capability_anchor
    target: {args.mature_path}
    reason: {cross_domain_reason}
status: shell_created
confirmed_facts:
  - {confirmed_fact}
assumptions:
  - {assumption}
unresolved_items:
  - {unresolved[0]}
  - {unresolved[1]}
current_blocker: ""
last_action: created_project_shell
next_recommended_action: {next_action}
tool_branch: {args.tool_branch}
system_change_status: {args.system_change_status}
motivated_by_user_goal: {args.user_goal}
key_refs:
  - projects/{project_id}/README.md
"""

    readme = f"""# {args.project_name}

## User Goal

{args.user_goal}

## Current Status

- project shell created
- target MCU: `{args.target_mcu}`
- closest mature AEL path: `{args.mature_path}`
- domain: `user_project_domain`
- project user: `{args.project_user}`

## Cross-Domain Links

- mature capability anchor: `{args.mature_path}`
- reason: {cross_domain_reason}

## Confirmed Facts

- {confirmed_fact}

## Assumptions

- {assumption}

## Unresolved Items

- {unresolved[0]}
- {unresolved[1]}

## Best Next Questions

- What exact setup/wiring is available for this board?
- What first example should be generated?
- What validation approach should be used first?
"""

    notes = f"""# {args.project_name} Session Notes

## Initial Creation

- project shell created
- user goal: {args.user_goal}
- target MCU: `{args.target_mcu}`
- closest mature AEL path: `{args.mature_path}`
- domain: `user_project_domain`
- project user: `{args.project_user}`

## Cross-Domain Link

- mature capability anchor: `{args.mature_path}`
- reason: {cross_domain_reason}

## Confirmed Facts

- {confirmed_fact}

## Assumptions

- {assumption}

## Unresolved Items

- {unresolved[0]}
- {unresolved[1]}

## Recommended Next Step

- {next_action}
"""

    _write(project_dir / "project.yaml", project_yaml)
    _write(project_dir / "README.md", readme)
    _write(project_dir / "session_notes.md", notes)
    print(f"created project shell: {project_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
