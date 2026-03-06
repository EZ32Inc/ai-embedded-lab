#!/usr/bin/env python3
"""
AEL Architecture Guard (v0.1)

Purpose:
    Enforce architectural boundary rules before commit.

Rules are loaded from:
    tools/ael_guard_rules.json

No third-party dependencies required.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = REPO_ROOT / "tools" / "ael_guard_rules.json"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _scan_file_patterns(path: Path, patterns: List[str]) -> List[Tuple[str, int, str]]:
    """
    Scan file for regex patterns.
    Returns list of (pattern, line_number, matched_line).
    """
    text = _read_text(path)
    results: List[Tuple[str, int, str]] = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        for pat in patterns:
            if re.search(pat, line, flags=re.IGNORECASE):
                results.append((pat, line_no, line.strip()))

    return results


def _run(cmd: List[str]) -> int:
    p = subprocess.run(cmd, cwd=str(REPO_ROOT))
    return int(p.returncode)


def _get_git_changed_files(cached: bool) -> Optional[Set[str]]:
    """
    Return changed file paths relative to repo root.
    Returns None when mode should fall back to full scan.
    """
    cmd = ["git", "diff", "--name-only"]
    if cached:
        cmd.append("--cached")
    try:
        res = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    if int(res.returncode) != 0:
        return None

    files = {line.strip() for line in (res.stdout or "").splitlines() if line.strip()}
    if not files:
        return None
    return files


# ---------------------------------------------------------------------------
# Rules Loader
# ---------------------------------------------------------------------------

def load_rules(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"Rules file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    required_fields = [
        "core_files",
        "docs_required",
        "core_forbidden_patterns",
        "adapter_heuristic_patterns",
    ]

    for field in required_fields:
        if field not in data:
            raise RuntimeError(f"Rules file missing field: '{field}'")
        if not isinstance(data[field], list):
            raise RuntimeError(f"Rules field '{field}' must be a list")
        if not data[field]:
            raise RuntimeError(f"Rules field '{field}' must not be empty")

        for idx, item in enumerate(data[field]):
            if not isinstance(item, str):
                raise RuntimeError(f"Invalid entry in '{field}' at index {idx}")

    optional_list_fields = ["core_forbidden_import_prefixes"]
    for field in optional_list_fields:
        if field not in data:
            data[field] = []
            continue
        if not isinstance(data[field], list):
            raise RuntimeError(f"Rules field '{field}' must be a list")
        for idx, item in enumerate(data[field]):
            if not isinstance(item, str):
                raise RuntimeError(f"Invalid entry in '{field}' at index {idx}")

    return data


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_docs(docs_required: List[str]) -> List[str]:
    errors: List[str] = []
    for rel in docs_required:
        if not (REPO_ROOT / rel).exists():
            errors.append(f"Missing required doc: {rel}")
    return errors


def check_core_contamination(core_files: List[str],
                             forbidden_patterns: List[str]) -> List[str]:
    errors: List[str] = []

    for rel in core_files:
        path = REPO_ROOT / rel
        if not path.exists():
            continue  # allow missing files silently

        hits = _scan_file_patterns(path, forbidden_patterns)
        for pat, line_no, line in hits:
            errors.append(
                f"CORE contamination in {rel}:{line_no} "
                f"(matches /{pat}/) -> {line}"
            )

    return errors


def check_core_forbidden_imports(core_files: List[str], prefixes: List[str]) -> List[str]:
    errors: List[str] = []
    if not prefixes:
        return errors

    import_patterns: List[Tuple[str, str]] = []
    for p in prefixes:
        escaped = re.escape(p)
        import_patterns.append((p, rf"^\s*from\s+{escaped}(?:\.|\s|$)"))
        import_patterns.append((p, rf"^\s*import\s+{escaped}(?:\.|\s|$)"))

    for rel in core_files:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        for line_no, line in enumerate(_read_text(path).splitlines(), start=1):
            for prefix, pat in import_patterns:
                if re.search(pat, line):
                    errors.append(
                        f"CORE dependency violation in {rel}:{line_no} "
                        f"(forbidden import prefix '{prefix}') -> {line.strip()}"
                    )
    return errors


def check_adapter_heuristics(patterns: List[str]) -> List[str]:
    errors: List[str] = []

    adapters_dir = REPO_ROOT / "ael" / "adapters"
    if not adapters_dir.exists():
        return errors

    for path in adapters_dir.rglob("*.py"):
        hits = _scan_file_patterns(path, patterns)
        for pat, line_no, line in hits:
            errors.append(
                f"Adapter heuristic smell in "
                f"{path.relative_to(REPO_ROOT)}:{line_no} "
                f"(matches /{pat}/) -> {line}"
            )

    return errors


def check_py_compile(paths: Iterable[str]) -> List[str]:
    errors: List[str] = []
    cmd = [sys.executable, "-m", "py_compile", *paths]
    if _run(cmd) != 0:
        errors.append("py_compile failed")
    return errors


def check_cli_smoke() -> List[str]:
    errors: List[str] = []
    res = subprocess.run(
        [sys.executable, "-m", "ael", "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if int(res.returncode) != 0:
        if res.stdout:
            print(res.stdout, end="")
        if res.stderr:
            print(res.stderr, end="", file=sys.stderr)
        errors.append("CLI smoke test failed: python -m ael --help")
    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true",
                        help="Run fast checks (recommended for pre-commit).")
    parser.add_argument("--compile", action="store_true",
                        help="Run py_compile validation.")
    parser.add_argument("--smoke", action="store_true",
                        help="Run CLI smoke test (non-hardware).")
    parser.add_argument("--staged", action="store_true",
                        help="Scan only staged files where applicable.")
    parser.add_argument("--changed", action="store_true",
                        help="Scan only modified (unstaged) files where applicable.")
    parser.add_argument("--rules", type=str,
                        default=str(DEFAULT_RULES_PATH),
                        help="Path to rules JSON file.")

    args = parser.parse_args()

    if args.fast:
        args.compile = True
        args.smoke = True
    if args.staged and args.changed:
        print("\n[AEL_GUARD] FAILED\n")
        print(" - Use only one mode: --staged or --changed")
        return 2

    try:
        rules = load_rules(Path(args.rules))
    except Exception as e:
        print("\n[AEL_GUARD] FAILED\n")
        print(" - Rules load error:", e)
        return 2

    errors: List[str] = []

    errors += check_docs(rules["docs_required"])
    staged_files: Optional[Set[str]] = None
    if args.staged:
        staged_files = _get_git_changed_files(cached=True)
    elif args.changed:
        staged_files = _get_git_changed_files(cached=False)

    if staged_files is None:
        core_files_to_scan = rules["core_files"]
    else:
        core_files_to_scan = [p for p in rules["core_files"] if p in staged_files]
    errors += check_core_contamination(
        core_files_to_scan,
        rules["core_forbidden_patterns"]
    )
    errors += check_core_forbidden_imports(
        core_files_to_scan,
        rules.get("core_forbidden_import_prefixes", []),
    )

    if staged_files is None:
        errors += check_adapter_heuristics(
            rules["adapter_heuristic_patterns"]
        )
    else:
        adapter_errors: List[str] = []
        for rel in sorted(staged_files):
            if not (rel.startswith("ael/adapters/") and rel.endswith(".py")):
                continue
            path = REPO_ROOT / rel
            if not path.exists():
                continue
            hits = _scan_file_patterns(path, rules["adapter_heuristic_patterns"])
            for pat, line_no, line in hits:
                adapter_errors.append(
                    f"Adapter heuristic smell in {rel}:{line_no} "
                    f"(matches /{pat}/) -> {line}"
                )
        errors += adapter_errors

    if args.compile:
        compile_targets: List[str] = []

        for rel in rules["core_files"]:
            if (REPO_ROOT / rel).exists():
                compile_targets.append(rel)

        adapters_dir = REPO_ROOT / "ael" / "adapters"
        if adapters_dir.exists():
            for p in adapters_dir.rglob("*.py"):
                compile_targets.append(str(p.relative_to(REPO_ROOT)))

        compile_targets.append(str((REPO_ROOT / "tools" / "ael_guard.py").relative_to(REPO_ROOT)))

        errors += check_py_compile(compile_targets)

    if args.smoke:
        errors += check_cli_smoke()

    if errors:
        print("\n[AEL_GUARD] FAILED\n")
        for e in errors:
            print(" -", e)
        print("\nRe-run after fixing issues:")
        print("  python3 tools/ael_guard.py --fast")
        return 2

    print("[AEL_GUARD] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
