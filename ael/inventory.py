from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ael import assets
from ael.connection_model import (
    build_connection_digest,
    build_connection_rows,
    build_connection_setup,
    diff_connection_setups,
    normalize_connection_context,
    render_connection_setup_text,
)
from ael.instrument_metadata import capability_names, validate_capability_surfaces, validate_communication
from ael.instruments.registry import InstrumentRegistry
from ael.instrument_view import build_resolved_instrument_inventory, render_resolved_instrument_inventory_text
from ael.pipeline import _simple_yaml_load
from ael.probe_binding import load_probe_binding
from ael.verification_model import summarize_resource_keys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_board_cfg(repo_root: Path, board_id: str) -> Dict[str, Any]:
    path = repo_root / "configs" / "boards" / f"{board_id}.yaml"
    if not path.exists():
        return {}
    raw = _simple_yaml_load(str(path))
    board = raw.get("board", {}) if isinstance(raw, dict) else {}
    return board if isinstance(board, dict) else {}


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


def _resolve_probe_or_instrument(root: Path, board_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(payload.get("instrument"), dict):
        inst = payload["instrument"]
        tcp = inst.get("tcp", {}) if isinstance(inst.get("tcp"), dict) else {}
        manifest = InstrumentRegistry().get(str(inst.get("id") or "")) or {}
        communication = manifest.get("communication", {}) if isinstance(manifest.get("communication"), dict) else {}
        return {
            "kind": "instrument",
            "id": inst.get("id"),
            "endpoint": {
                "host": tcp.get("host"),
                "port": tcp.get("port"),
            } if tcp else None,
            "communication": communication,
            "capability_surfaces": manifest.get("capability_surfaces", {}) if isinstance(manifest.get("capability_surfaces"), dict) else {},
            "metadata_validation_errors": (
                validate_communication(communication)
                + validate_capability_surfaces(
                    manifest.get("capability_surfaces"),
                    capabilities=capability_names(manifest),
                    communication=communication,
                )
            ),
        }
    board_cfg = _load_board_cfg(root, board_id)
    instance_id = str(
        board_cfg.get("control_instrument_instance")
        or board_cfg.get("instrument_instance")
        or ""
    ).strip() or None
    probe_path = str(
        board_cfg.get("control_instrument_config")
        or board_cfg.get("probe_config")
        or ""
    ).strip() or None
    binding = load_probe_binding(root, probe_path=probe_path, instance_id=instance_id)
    return {
        "kind": "control_instrument",
        "legacy_kind": "probe",
        "id": binding.instance_id or binding.raw.get("probe", {}).get("name") or "ESP32JTAG",
        "type": binding.type_id,
        "instrument_role": "control",
        "endpoint": {
            "host": binding.endpoint_host,
            "port": binding.endpoint_port,
        } if (binding.endpoint_host or binding.endpoint_port is not None) else None,
        "communication": binding.communication,
        "capability_surfaces": binding.capability_surfaces,
        "metadata_validation_errors": list(binding.metadata_validation_errors),
    }


def _primary_selected_instrument(poi: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(poi, dict):
        return {}
    kind = str(poi.get("kind") or "").strip()
    if kind == "control_instrument":
        return {
            "kind": "control_instrument",
            "legacy_kind": poi.get("legacy_kind"),
            "id": poi.get("id"),
            "type": poi.get("type"),
            "instrument_role": poi.get("instrument_role") or "control",
            "endpoint": poi.get("endpoint"),
            "communication": dict(poi.get("communication") or {}),
            "capability_surfaces": dict(poi.get("capability_surfaces") or {}),
            "metadata_validation_errors": list(poi.get("metadata_validation_errors") or []),
        }
    return dict(poi)


def _selected_dut_payload(root: Path, board_id: str, board_cfg: Dict[str, Any]) -> Dict[str, Any]:
    dut = assets.load_dut_prefer_user(board_id)
    manifest = dut.get("manifest") if isinstance(dut, dict) and isinstance(dut.get("manifest"), dict) else {}
    return {
        "id": board_id,
        "name": manifest.get("description") or board_cfg.get("name"),
        "target": board_cfg.get("target"),
        "mcu": manifest.get("mcu") or board_cfg.get("target"),
        "family": manifest.get("family"),
        "source": "user" if isinstance(dut, dict) and "/assets_user/" in str(dut.get("path") or "") else ("golden" if dut else None),
    }


def _selected_board_profile_payload(root: Path, board_id: str, board_cfg: Dict[str, Any]) -> Dict[str, Any]:
    board_path = root / "configs" / "boards" / f"{board_id}.yaml"
    return {
        "id": board_id,
        "name": board_cfg.get("name"),
        "target": board_cfg.get("target"),
        "config": board_path.relative_to(root).as_posix() if board_path.exists() else None,
    }


def _selected_bench_resources_payload(selected_instrument: Dict[str, Any], connection_setup: Dict[str, Any]) -> Dict[str, Any]:
    resource_keys = []
    kind = str(selected_instrument.get("kind") or "").strip()
    endpoint = selected_instrument.get("endpoint") if isinstance(selected_instrument.get("endpoint"), dict) else {}
    if kind == "control_instrument":
        if endpoint.get("host") and endpoint.get("port") is not None:
            resource_keys.append(f"probe:{endpoint.get('host')}:{endpoint.get('port')}")
        elif selected_instrument.get("config"):
            resource_keys.append(f"probe_path:{selected_instrument.get('config')}")
    elif kind == "instrument":
        inst_id = selected_instrument.get("id")
        if inst_id and endpoint.get("host") and endpoint.get("port") is not None:
            resource_keys.append(f"instrument:{inst_id}:{endpoint.get('host')}:{endpoint.get('port')}")
    return {
        "selected_instrument": dict(selected_instrument or {}),
        "resource_keys": resource_keys,
        "resource_summary": summarize_resource_keys(resource_keys),
        "connection_setup": dict(connection_setup or {}),
        "connection_digest": build_connection_digest(connection_setup),
    }


def _build_expected_checks(board_cfg: Dict[str, Any], payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    if payload.get("pin"):
        checks.append(
            {
                "type": "signal",
                "pin": payload.get("pin"),
                "min_freq_hz": payload.get("min_freq_hz"),
                "max_freq_hz": payload.get("max_freq_hz"),
                "duty_min": payload.get("duty_min"),
                "duty_max": payload.get("duty_max"),
                "duration_s": payload.get("duration_s"),
                "min_edges": payload.get("min_edges"),
                "max_edges": payload.get("max_edges"),
            }
        )
    uart = payload.get("observe_uart", {}) if isinstance(payload.get("observe_uart"), dict) else {}
    if uart.get("enabled"):
        checks.append(
            {
                "type": "uart",
                "baud": uart.get("baud"),
                "duration_s": uart.get("duration_s"),
                "expect_patterns": uart.get("expect_patterns"),
            }
        )
    if isinstance(payload.get("uart_expect"), dict):
        checks.append({"type": "uart_expect", **payload.get("uart_expect")})
    if isinstance(payload.get("instrument"), dict):
        measure = payload.get("instrument", {}).get("measure", {})
        if isinstance(measure, dict):
            checks.append({"type": "instrument_measure", **measure})
    led_observe = payload.get("observe_led", {}) if isinstance(payload.get("observe_led"), dict) else {}
    if led_observe.get("enabled"):
        checks.append(
            {
                "type": "led",
                "pin": led_observe.get("pin") or "led",
                "duration_s": led_observe.get("duration_s"),
                "min_edges": led_observe.get("min_edges"),
                "max_edges": led_observe.get("max_edges"),
                "expected_hz": led_observe.get("expected_hz"),
            }
        )
    return checks

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


def build_instrument_instance_inventory(repo_root: Path | None = None) -> Dict[str, Any]:
    return build_resolved_instrument_inventory(repo_root or REPO_ROOT)


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


def describe_test(board_id: str, test_path: str, repo_root: Path | None = None) -> Dict[str, Any]:
    root = Path(repo_root or REPO_ROOT)
    path = Path(test_path)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        return {"ok": False, "error": f"test not found: {test_path}"}

    payload = _load_json(path)
    board_cfg = _load_board_cfg(root, board_id)
    connection_ctx = normalize_connection_context(
        board_cfg,
        payload,
        required_wiring=["swd", "reset", "verify"],
    )
    selected_instrument = _primary_selected_instrument(_resolve_probe_or_instrument(root, board_id, payload))
    connection_setup = build_connection_setup(connection_ctx)
    result = {
        "ok": True,
        "board": board_id,
        "test": {
            "name": payload.get("name") or path.stem,
            "path": path.relative_to(root).as_posix(),
            "validation_style": _infer_validation_style(payload),
        },
        "selected_dut": _selected_dut_payload(root, board_id, board_cfg),
        "selected_board_profile": _selected_board_profile_payload(root, board_id, board_cfg),
        "selected_instrument": selected_instrument,
        "selected_bench_resources": _selected_bench_resources_payload(selected_instrument, connection_setup),
        "connections": build_connection_rows(connection_ctx, payload),
        "expected_checks": _build_expected_checks(board_cfg, payload),
        "board_context": {
            "target": board_cfg.get("target"),
            "clock_hz": board_cfg.get("clock_hz"),
            "observe_map": dict(connection_ctx.observe_map),
            "verification_views": dict(connection_ctx.verification_views),
            "default_wiring": dict(connection_ctx.default_wiring),
        },
        "connection_setup": connection_setup,
        "notes": payload.get("notes"),
        "warnings": [f"warning: {item}" for item in connection_ctx.warnings],
    }
    legacy = _resolve_probe_or_instrument(root, board_id, payload)
    if legacy.get("legacy_kind"):
        result["compatibility"] = {"probe_or_instrument": legacy}
    return result


def describe_connection(board_id: str, test_path: str, repo_root: Path | None = None) -> Dict[str, Any]:
    payload = describe_test(board_id=board_id, test_path=test_path, repo_root=repo_root)
    if not payload.get("ok"):
        return payload
    return {
        "ok": True,
        "board": payload.get("board"),
        "test": payload.get("test"),
        "connection_setup": payload.get("connection_setup"),
        "connections": payload.get("connections"),
        "warnings": payload.get("warnings"),
        "validation_errors": (
            payload.get("connection_setup", {}).get("validation_errors")
            if isinstance(payload.get("connection_setup"), dict)
            else []
        ),
        "source_summary": (
            payload.get("connection_setup", {}).get("source_summary")
            if isinstance(payload.get("connection_setup"), dict)
            else {}
        ),
    }


def diff_connection(
    *,
    board_id: str,
    test_path: str,
    against_board: str,
    against_test: str,
    repo_root: Path | None = None,
) -> Dict[str, Any]:
    left = describe_connection(board_id=board_id, test_path=test_path, repo_root=repo_root)
    if not left.get("ok"):
        return left
    right = describe_connection(board_id=against_board, test_path=against_test, repo_root=repo_root)
    if not right.get("ok"):
        return right
    diff = diff_connection_setups(
        left.get("connection_setup"),
        right.get("connection_setup"),
        left_label=f"{board_id}:{test_path}",
        right_label=f"{against_board}:{against_test}",
    )
    return {
        "ok": True,
        "left": {"board": left.get("board"), "test": left.get("test")},
        "right": {"board": right.get("board"), "test": right.get("test")},
        "diff": diff,
    }


def render_describe_text(payload: Dict[str, Any]) -> str:
    if not payload.get("ok"):
        return f"error: {payload.get('error')}\n"
    lines: List[str] = []
    lines.append(f"board: {payload.get('board')}")
    test = payload.get("test", {})
    lines.append(f"test: {test.get('name')} ({test.get('path')})")
    dut = payload.get("selected_dut", {})
    if isinstance(dut, dict) and dut:
        lines.append(f"selected_dut: {dut.get('id')}")
        if dut.get("name"):
            lines.append(f"dut_name: {dut.get('name')}")
        if dut.get("target"):
            lines.append(f"dut_target: {dut.get('target')}")
    board_profile = payload.get("selected_board_profile", {})
    if isinstance(board_profile, dict) and board_profile:
        lines.append(f"selected_board_profile: {board_profile.get('id')}")
        if board_profile.get("config"):
            lines.append(f"board_profile_config: {board_profile.get('config')}")
    poi = payload.get("selected_instrument", {})
    lines.append(f"{poi.get('kind')}: {poi.get('id')}")
    if poi.get("legacy_kind") and poi.get("legacy_kind") != poi.get("kind"):
        lines.append(f"legacy_kind: {poi.get('legacy_kind')}")
    if poi.get("type"):
        lines.append(f"type: {poi.get('type')}")
    endpoint = poi.get("endpoint")
    if isinstance(endpoint, dict) and (endpoint.get("host") or endpoint.get("port")):
        lines.append(f"endpoint: {endpoint.get('host')}:{endpoint.get('port')}")
    if isinstance(poi.get("communication"), dict) and poi.get("communication"):
        lines.append("communication:")
        for key, value in (poi.get("communication") or {}).items():
            lines.append(f"  - {key}: {value}")
    if isinstance(poi.get("capability_surfaces"), dict) and poi.get("capability_surfaces"):
        lines.append("capability_surfaces:")
        for key, value in (poi.get("capability_surfaces") or {}).items():
            lines.append(f"  - {key}: {value}")
    if poi.get("metadata_validation_errors"):
        lines.append("metadata_validation_errors:")
        for item in poi.get("metadata_validation_errors") or []:
            lines.append(f"  - {item}")
    conn_setup = payload.get("connection_setup", {})
    if isinstance(conn_setup, dict) and conn_setup:
        lines.append("connection_setup:")
        lines.extend(render_connection_setup_text(conn_setup, indent="  "))
    bench = payload.get("selected_bench_resources", {})
    if isinstance(bench, dict) and bench.get("connection_digest"):
        lines.append(f"connection_digest: {'; '.join(bench.get('connection_digest', []))}")
    lines.append("connections:")
    for conn in payload.get("connections", []):
        extra = []
        if conn.get("expect"):
            extra.append(str(conn.get("expect")))
        if conn.get("freq_hz") is not None:
            extra.append(f"{conn.get('freq_hz')}Hz")
        if conn.get("expect_v_min") is not None and conn.get("expect_v_max") is not None:
            extra.append(f"{conn.get('expect_v_min')}..{conn.get('expect_v_max')}V")
        suffix = f" ({', '.join(extra)})" if extra else ""
        lines.append(f"  - {conn.get('from')} -> {conn.get('to')}{suffix}")
    lines.append("expected_checks:")
    for check in payload.get("expected_checks", []):
        lines.append(f"  - {check.get('type')}: {json.dumps(check, sort_keys=True)}")
    for warning in payload.get("warnings", []):
        lines.append(warning)
    if payload.get("notes"):
        lines.append(f"notes: {payload.get('notes')}")
    return "\n".join(lines).rstrip() + "\n"


def render_connection_text(payload: Dict[str, Any]) -> str:
    if not payload.get("ok"):
        return f"error: {payload.get('error')}\n"
    lines: List[str] = []
    lines.append(f"board: {payload.get('board')}")
    test = payload.get("test", {})
    lines.append(f"test: {test.get('name')} ({test.get('path')})")
    lines.append("connection_setup:")
    lines.extend(render_connection_setup_text(payload.get("connection_setup"), indent="  "))
    lines.append("connections:")
    for conn in payload.get("connections", []):
        extra = []
        if conn.get("expect"):
            extra.append(str(conn.get("expect")))
        if conn.get("freq_hz") is not None:
            extra.append(f"{conn.get('freq_hz')}Hz")
        if conn.get("expect_v_min") is not None and conn.get("expect_v_max") is not None:
            extra.append(f"{conn.get('expect_v_min')}..{conn.get('expect_v_max')}V")
        if conn.get("required") is True:
            extra.append("required")
        suffix = f" ({', '.join(extra)})" if extra else ""
        lines.append(f"  - {conn.get('from')} -> {conn.get('to')}{suffix}")
    return "\n".join(lines).rstrip() + "\n"


def render_connection_diff_text(payload: Dict[str, Any]) -> str:
    if not payload.get("ok"):
        return f"error: {payload.get('error')}\n"
    diff = payload.get("diff", {}) if isinstance(payload.get("diff"), dict) else {}
    left = payload.get("left", {}) if isinstance(payload.get("left"), dict) else {}
    right = payload.get("right", {}) if isinstance(payload.get("right"), dict) else {}
    lines: List[str] = []
    lines.append(f"left: {left.get('board')} ({(left.get('test') or {}).get('path')})")
    lines.append(f"right: {right.get('board')} ({(right.get('test') or {}).get('path')})")
    lines.append(f"same: {diff.get('same')}")
    lines.append("left_only:")
    for item in diff.get("left_only", []) or []:
        lines.append(f"  - {item}")
    lines.append("right_only:")
    for item in diff.get("right_only", []) or []:
        lines.append(f"  - {item}")
    return "\n".join(lines).rstrip() + "\n"


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


def render_instance_text(payload: Dict[str, Any]) -> str:
    return render_resolved_instrument_inventory_text(payload)
