from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
from typing import Any, Dict, List, Tuple

from ael import assets
from ael.instruments.registry import InstrumentRegistry
from ael.pipeline import _simple_yaml_load
from ael.probe_binding import load_probe_binding


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
        }
    board_cfg = _load_board_cfg(root, board_id)
    instance_id = str(board_cfg.get("instrument_instance") or "").strip() or None
    probe_path = str(board_cfg.get("probe_config") or "").strip() or None
    binding = load_probe_binding(root, probe_path=probe_path, instance_id=instance_id)
    return {
        "kind": "probe",
        "id": binding.instance_id or binding.raw.get("probe", {}).get("name") or "ESP32JTAG",
        "type": binding.type_id,
        "endpoint": {
            "host": binding.endpoint_host,
            "port": binding.endpoint_port,
        } if (binding.endpoint_host or binding.endpoint_port is not None) else None,
        "communication": binding.communication,
        "capability_surfaces": binding.capability_surfaces,
    }


def _build_connections(board_cfg: Dict[str, Any], payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    bench = payload.get("bench_setup", {}) if isinstance(payload.get("bench_setup"), dict) else {}
    conns: List[Dict[str, Any]] = []
    wiring = board_cfg.get("default_wiring", {}) if isinstance(board_cfg.get("default_wiring"), dict) else {}
    observe_map = board_cfg.get("observe_map", {}) if isinstance(board_cfg.get("observe_map"), dict) else {}
    bench_connections = board_cfg.get("bench_connections", []) if isinstance(board_cfg.get("bench_connections"), list) else []

    if isinstance(payload.get("instrument"), dict):
        for item in bench.get("dut_to_instrument", []) if isinstance(bench.get("dut_to_instrument"), list) else []:
            if not isinstance(item, dict):
                continue
            conn = {
                "from": item.get("dut_gpio"),
                "to": f"inst GPIO{item.get('inst_gpio')}",
                "expect": item.get("expect"),
            }
            if item.get("freq_hz") is not None:
                conn["freq_hz"] = item.get("freq_hz")
            conns.append(conn)
        for item in bench.get("dut_to_instrument_analog", []) if isinstance(bench.get("dut_to_instrument_analog"), list) else []:
            if not isinstance(item, dict):
                continue
            conn = {
                "from": item.get("dut_signal"),
                "to": f"inst ADC GPIO{item.get('inst_adc_gpio')}",
                "expect_v_min": item.get("expect_v_min"),
                "expect_v_max": item.get("expect_v_max"),
            }
            if item.get("avg") is not None:
                conn["avg"] = item.get("avg")
            conns.append(conn)
        if bench.get("ground_required"):
            conns.append({"from": "GND", "to": "inst GND", "required": True})
        return conns

    if wiring.get("swd"):
        conns.append({"from": "SWD", "to": wiring.get("swd")})
    if "reset" in wiring:
        conns.append({"from": "RESET", "to": wiring.get("reset")})
    for item in bench_connections:
        if not isinstance(item, dict):
            continue
        src = item.get("from")
        dst = item.get("to")
        if src and dst:
            conns.append({"from": src, "to": dst})
    if conns and len(conns) > 2:
        return conns
    pin = payload.get("pin")
    if pin:
        resolved = observe_map.get(str(pin), wiring.get("verify"))
        signal_name = str(pin)
        observed_label = signal_name
        if signal_name == "sig":
            for key, value in observe_map.items():
                if key != "sig" and value == observe_map.get("sig"):
                    observed_label = key.upper() if key.startswith("pa") or key.startswith("pb") or key.startswith("pc") else key
                    break
        conns.append({"from": observed_label, "to": resolved})
    return conns


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


def _connection_warnings(board_cfg: Dict[str, Any]) -> List[str]:
    bench_connections = board_cfg.get("bench_connections", []) if isinstance(board_cfg.get("bench_connections"), list) else []
    from_counts = Counter()
    for item in bench_connections:
        if not isinstance(item, dict):
            continue
        src = str(item.get("from") or "").strip()
        if src:
            from_counts[src] += 1
    warnings: List[str] = []
    for src, count in sorted(from_counts.items()):
        if count > 1:
            warnings.append(
                f"warning: MCU pin {src} is connected to {count} observation points; verify signal loading, shared ground, and whether the instrument supports parallel observation on that net."
            )
    return warnings


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


def _board_reference_index(root: Path) -> tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    probe_refs: Dict[str, List[str]] = {}
    instrument_refs: Dict[str, List[str]] = {}
    boards_dir = root / "configs" / "boards"
    if not boards_dir.exists():
        return probe_refs, instrument_refs
    for path in sorted(boards_dir.glob("*.yaml")):
        raw = _simple_yaml_load(str(path))
        board_cfg = raw.get("board", {}) if isinstance(raw, dict) else {}
        if not isinstance(board_cfg, dict):
            continue
        board_id = path.stem
        instance_id = str(board_cfg.get("instrument_instance") or "").strip()
        if instance_id:
            probe_refs.setdefault(instance_id, []).append(board_id)
        instrument_cfg = board_cfg.get("instrument", {}) if isinstance(board_cfg.get("instrument"), dict) else {}
        instrument_id = str(instrument_cfg.get("id") or "").strip()
        if instrument_id:
            instrument_refs.setdefault(instrument_id, []).append(board_id)
    return probe_refs, instrument_refs


def _plan_reference_index(root: Path) -> Dict[str, List[str]]:
    refs: Dict[str, List[str]] = {}
    plans_dir = root / "tests" / "plans"
    if not plans_dir.exists():
        return refs
    for path in sorted(plans_dir.glob("*.json")):
        payload = _load_json(path)
        instrument_cfg = payload.get("instrument", {}) if isinstance(payload.get("instrument"), dict) else {}
        instrument_id = str(instrument_cfg.get("id") or "").strip()
        if instrument_id:
            refs.setdefault(instrument_id, []).append(path.relative_to(root).as_posix())
    return refs


def build_instrument_instance_inventory(repo_root: Path | None = None) -> Dict[str, Any]:
    root = Path(repo_root or REPO_ROOT)
    probe_board_refs, instrument_board_refs = _board_reference_index(root)
    instrument_plan_refs = _plan_reference_index(root)

    probe_instances: List[Dict[str, Any]] = []
    instances_dir = root / "configs" / "instrument_instances"
    if instances_dir.exists():
        for path in sorted(instances_dir.glob("*.yaml")):
            binding = load_probe_binding(root, instance_id=path.stem)
            probe_instances.append(
                {
                    "kind": "probe_instance",
                    "id": binding.instance_id,
                    "type": binding.type_id,
                    "config_path": path.relative_to(root).as_posix(),
                    "endpoint": {
                        "host": binding.endpoint_host,
                        "port": binding.endpoint_port,
                    } if (binding.endpoint_host or binding.endpoint_port is not None) else None,
                    "communication": dict(binding.communication or {}),
                    "capability_surfaces": dict(binding.capability_surfaces or {}),
                    "referenced_by": {
                        "boards": sorted(probe_board_refs.get(str(binding.instance_id), [])),
                    },
                }
            )

    instruments: List[Dict[str, Any]] = []
    registry = InstrumentRegistry()
    for manifest in registry.list():
        instrument_id = str(manifest.get("id") or "").strip()
        instruments.append(
            {
                "kind": "instrument",
                "id": instrument_id,
                "origin": manifest.get("_origin"),
                "manifest_path": (
                    Path(str(manifest.get("_path"))).relative_to(root).as_posix()
                    if str(manifest.get("_path") or "").startswith(str(root))
                    else manifest.get("_path")
                ),
                "communication": dict(manifest.get("communication") or {}),
                "capability_surfaces": dict(manifest.get("capability_surfaces") or {}),
                "referenced_by": {
                    "boards": sorted(instrument_board_refs.get(instrument_id, [])),
                    "plans": sorted(instrument_plan_refs.get(instrument_id, [])),
                },
            }
        )

    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(root),
        "summary": {
            "probe_instance_count": len(probe_instances),
            "instrument_count": len(instruments),
        },
        "probe_instances": probe_instances,
        "instruments": instruments,
    }


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
    wiring = board_cfg.get("default_wiring", {}) if isinstance(board_cfg.get("default_wiring"), dict) else {}
    observe_map = board_cfg.get("observe_map", {}) if isinstance(board_cfg.get("observe_map"), dict) else {}
    result = {
        "ok": True,
        "board": board_id,
        "test": {
            "name": payload.get("name") or path.stem,
            "path": path.relative_to(root).as_posix(),
            "validation_style": _infer_validation_style(payload),
        },
        "probe_or_instrument": _resolve_probe_or_instrument(root, board_id, payload),
        "connections": _build_connections(board_cfg, payload),
        "expected_checks": _build_expected_checks(board_cfg, payload),
        "board_context": {
            "target": board_cfg.get("target"),
            "clock_hz": board_cfg.get("clock_hz"),
            "observe_map": observe_map,
            "verification_views": (board_cfg.get("verification_views", {}) if isinstance(board_cfg.get("verification_views"), dict) else {}),
            "default_wiring": wiring,
        },
        "notes": payload.get("notes"),
        "warnings": _connection_warnings(board_cfg),
    }
    return result


def render_describe_text(payload: Dict[str, Any]) -> str:
    if not payload.get("ok"):
        return f"error: {payload.get('error')}\n"
    lines: List[str] = []
    lines.append(f"board: {payload.get('board')}")
    test = payload.get("test", {})
    lines.append(f"test: {test.get('name')} ({test.get('path')})")
    poi = payload.get("probe_or_instrument", {})
    lines.append(f"{poi.get('kind')}: {poi.get('id')}")
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
    if not payload.get("ok"):
        return f"error: {payload.get('error')}\n"
    lines: List[str] = []
    summary = payload.get("summary") or {}
    lines.append("Instrument instances")
    lines.append(f"probe_instance_count: {summary.get('probe_instance_count', 0)}")
    lines.append(f"instrument_count: {summary.get('instrument_count', 0)}")
    lines.append("")
    for item in payload.get("probe_instances") or []:
        lines.append(f"{item.get('id')} ({item.get('type')})")
        endpoint = item.get("endpoint")
        if isinstance(endpoint, dict) and (endpoint.get("host") or endpoint.get("port") is not None):
            lines.append(f"  endpoint: {endpoint.get('host')}:{endpoint.get('port')}")
        refs = (item.get("referenced_by") or {}).get("boards") or []
        if refs:
            lines.append(f"  boards: {', '.join(refs)}")
    if payload.get("probe_instances"):
        lines.append("")
    for item in payload.get("instruments") or []:
        lines.append(f"{item.get('id')} ({item.get('origin')})")
        refs = item.get("referenced_by") or {}
        boards = refs.get("boards") or []
        plans = refs.get("plans") or []
        if boards:
            lines.append(f"  boards: {', '.join(boards)}")
        if plans:
            lines.append(f"  plans: {', '.join(plans)}")
    return "\n".join(lines).rstrip() + "\n"
