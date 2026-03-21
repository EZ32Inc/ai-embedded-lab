"""Post-run helpers for verify-default: regression snapshot auto-save and actionable hint summary.

Separated from ael/__main__.py (a CORE file) because these functions import from
ael_controlplane, which is forbidden in CORE files per ael_guard_rules.json.
"""
from pathlib import Path


def autosave_regression_snapshot(
    state: dict,
    setting_file: str,
    report_root: str = "reports",
) -> None:
    """Build, save, and print a regression snapshot after a verify-default run.

    ``state`` is the dict returned by ``_verify_default_state`` in __main__.py.
    """
    try:
        from ael_controlplane.bench_regression import (
            build_regression_snapshot,
            save_regression_snapshot,
            load_regression_history,
            compare_regression_run,
            render_regression_comparison_text,
        )
        pass_count = len(state.get("validated_tests") or [])
        fail_count = len(state.get("failing_tests") or [])
        total_count = pass_count + fail_count + len(state.get("optional_failing_tests") or [])
        augmented = dict(state)
        augmented["pass_count"] = pass_count
        augmented["fail_count"] = fail_count
        augmented["total_count"] = total_count
        augmented["ok"] = fail_count == 0
        snapshot = build_regression_snapshot(augmented)
        history = load_regression_history(report_root)
        log_path = save_regression_snapshot(snapshot, report_root)
        comparison = compare_regression_run(snapshot, history)
        print(render_regression_comparison_text(snapshot, comparison), end="")
        print(f"regression_snapshot saved: {log_path}")
    except Exception as exc:
        print(f"warning: regression snapshot not saved: {exc}")


def print_regression_history_section(report_root: str = "reports", count: int = 5) -> None:
    """Print the last ``count`` regression snapshots for verify-default review."""
    try:
        from ael_controlplane.bench_regression import (
            load_regression_history,
            compare_regression_run,
            render_regression_comparison_text,
        )
        history = load_regression_history(report_root, count=count + 1)
        if not history:
            print("regression_history: no snapshots recorded")
            return
        print(f"regression_history: last {min(count, len(history))} snapshot(s)")
        displayed = history[-count:]
        for snap in displayed:
            prior = history[:history.index(snap)]
            comparison = compare_regression_run(snap, prior)
            print(render_regression_comparison_text(snap, comparison), end="")
    except Exception as exc:
        print(f"warning: could not load regression history: {exc}")


def print_actionable_hints(state: dict, runs_root: str = "runs") -> None:
    """Scan flash.log of failed boards and print an ACTION REQUIRED block when hints are found.

    ``state`` is the dict returned by ``_verify_default_state`` in __main__.py.
    """
    try:
        all_failing = list(state.get("failing_tests") or []) + list(state.get("optional_failing_tests") or [])
        if not all_failing:
            return
        runs_dir = Path(runs_root)
        hints_by_board: dict = {}
        for entry in all_failing:
            run_id = entry.get("run_id")
            step = str(entry.get("step", ""))
            if not run_id:
                continue
            flash_log = runs_dir / run_id / "flash.log"
            if not flash_log.exists():
                continue
            text = flash_log.read_text(encoding="utf-8", errors="replace")
            seen: set = set()
            lines: list = []
            for line in text.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if (
                    stripped.startswith("Flash: diagnostic")
                    or stripped.startswith("Flash: ST-Link USB transport is frozen")
                    or "unplug" in stripped.lower()
                ):
                    if stripped not in seen:
                        seen.add(stripped)
                        lines.append(stripped)
            if lines:
                hints_by_board[step] = lines
        if not hints_by_board:
            return
        print()
        print("=" * 60)
        print("ACTION REQUIRED — failed board diagnostics")
        print("=" * 60)
        for step, lines in hints_by_board.items():
            print(f"  [{step}]")
            for line in lines:
                print(f"    {line}")
        print("=" * 60)
    except Exception as exc:
        print(f"warning: actionable hints not printed: {exc}")
