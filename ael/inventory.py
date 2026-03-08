from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ael import assets


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_plan_index(repo_root: Path) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    plans_dir = repo_root / "tests" / "plans"
    plans_by_path: Dict[str, Dict[str, Any]] = {}
    generic_plans: List[Dict[str, Any]] = []
    if not plans_dir.exists():
        return plans_by_path, generic_plans

    for path in sorted(plans_dir.glob("*.json")):
        payload = _load_json(path)
        rel = path.relative_to(repo_root).as_posix()
        entry = {
            "name": payload.get("name") or path.stem,
            "path": rel,
            "board": payload.get("board"),
            "dut": payload.get("dut"),
            "validation_style": _infer_validation_style(payload),
        }
        plans_by_path[rel] = entry
        if not entry["board"] and not entry["dut"]:
            generic_plans.append(entry)
    return plans_by_path, generic_plans


def _load_pack_index(repo_root: Path) -> List[Dict[str, Any]]:
    packs: List[Dict[str, Any]] = []
    pack_dirs = [repo_root / "packs"]
    for root in (repo_root / "assets_golden" / "duts", repo_root / "assets_user" / "duts"):
        if root.exists():
            for path in root.glob("*/packs"):
                pack_dirs.append(path)

    seen = set()
    for pack_dir in pack_dirs:
        if not pack_dir.exists():
            continue
        for path in sorted(pack_dir.glob("*.json")):
            rel = path.relative_to(repo_root).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            payload = _load_json(path)
            packs.append(
                {
                    "name": payload.get("name") or path.stem,
                    "path": rel,
                    "board": payload.get("board"),
                    "tests": [str(t) for t in (payload.get("tests") or [])],
                }
            )
    return packs


def _infer_validation_style(payload: Dict[str, Any]) -> str:
    if isinstance(payload.get("instrument"), dict):
        return "meter"
    if payload.get("selftest"):
        return "instrument_selftest"
    if payload.get("observe_uart"):
        return "uart_or_signal"
    if payload.get("pin"):
        return "signal"
    return "generic"


def _merge_tests(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for item in items:
        key = (str(item.get("path") or ""), str(item.get("name") or ""))
        current = merged.get(key)
        source = {"via": item.get("via")}
        if item.get("pack"):
            source["pack"] = item.get("pack")
        if item.get("missing"):
            source["missing"] = True
        if current is None:
            current = {
                "name": item.get("name"),
                "path": item.get("path"),
                "validation_style": item.get("validation_style"),
                "missing": bool(item.get("missing")),
                "sources": [source],
            }
            merged[key] = current
        else:
            if item.get("missing"):
                current["missing"] = True
            if source not in current["sources"]:
                current["sources"].append(source)
    return list(merged.values())


def build_inventory(repo_root: Path | None = None) -> Dict[str, Any]:
    root = Path(repo_root or REPO_ROOT)
    plans_by_path, generic_plans = _load_plan_index(root)
    packs = _load_pack_index(root)

    dut_entries: List[Dict[str, Any]] = []
    all_duts = []
    for source_name, source_root in (("golden", root / "assets_golden" / "duts"), ("user", root / "assets_user" / "duts")):
        if not source_root.exists():
            continue
        for entry in assets.list_duts(source_root):
            manifest = entry.get("manifest") or {}
            dut_id = str(manifest.get("id") or entry.get("id") or Path(entry["path"]).name)
            tests: List[Dict[str, Any]] = []
            for plan in plans_by_path.values():
                if plan.get("board") == dut_id or plan.get("dut") == dut_id:
                    tests.append(
                        {
                            "name": plan["name"],
                            "path": plan["path"],
                            "via": "direct_plan",
                            "validation_style": plan["validation_style"],
                        }
                    )
            for pack in packs:
                if pack.get("board") != dut_id:
                    continue
                for test_path in pack.get("tests") or []:
                    rel = str(test_path)
                    plan = plans_by_path.get(rel)
                    if plan:
                        tests.append(
                            {
                                "name": plan["name"],
                                "path": rel,
                                "via": "pack",
                                "pack": pack["name"],
                                "validation_style": plan["validation_style"],
                            }
                        )
                    else:
                        tests.append(
                            {
                                "name": Path(rel).stem,
                                "path": rel,
                                "via": "pack",
                                "pack": pack["name"],
                                "validation_style": "unknown",
                                "missing": True,
                            }
                        )
            tests = _merge_tests(tests)
            board_config = root / "configs" / "boards" / f"{dut_id}.yaml"
            dut_entries.append(
                {
                    "dut_id": dut_id,
                    "mcu": manifest.get("mcu"),
                    "family": manifest.get("family"),
                    "description": manifest.get("description"),
                    "source": source_name,
                    "board_config": board_config.relative_to(root).as_posix() if board_config.exists() else None,
                    "verified_status": bool((manifest.get("verified") or {}).get("status")) if isinstance(manifest.get("verified"), dict) else None,
                    "tests": tests,
                }
            )
            all_duts.append(dut_id)

    mcus_with_tests = sorted({str(item.get("mcu")) for item in dut_entries if item.get("mcu") and item.get("tests")})
    duts_with_tests = sorted([item["dut_id"] for item in dut_entries if item.get("tests")])
    all_test_names = sorted({test["name"] for item in dut_entries for test in item.get("tests", []) if test.get("name")})
    inventory = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(root),
        "summary": {
            "dut_count": len(dut_entries),
            "duts_with_tests": duts_with_tests,
            "mcus_with_tests": mcus_with_tests,
            "test_names": all_test_names,
        },
        "duts": sorted(dut_entries, key=lambda item: item["dut_id"]),
        "generic_tests": generic_plans,
    }
    return inventory


def render_text(inventory: Dict[str, Any]) -> str:
    lines: List[str] = []
    summary = inventory.get("summary") or {}
    lines.append("DUT inventory")
    lines.append(f"dut_count: {summary.get('dut_count', 0)}")
    lines.append("mcus_with_tests: " + ", ".join(summary.get("mcus_with_tests") or []))
    lines.append("")
    for dut in inventory.get("duts") or []:
        lines.append(f"{dut['dut_id']} ({dut.get('mcu')})")
        tests = dut.get("tests") or []
        if not tests:
            lines.append("  tests: none")
            continue
        for test in tests:
            extras = []
            for source in test.get("sources") or []:
                via = source.get("via")
                if source.get("pack"):
                    via = f"{via}, pack={source['pack']}"
                if source.get("missing"):
                    via = f"{via}, missing"
                extras.append(via)
            lines.append(f"  - {test.get('name')} [{' ; '.join([e for e in extras if e])}]")
        lines.append("")
    generic = inventory.get("generic_tests") or []
    if generic:
        lines.append("generic_tests")
        for test in generic:
            lines.append(f"  - {test.get('name')} ({test.get('path')})")
    return "\n".join(lines).rstrip() + "\n"
