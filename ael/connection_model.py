from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ael.connection_metadata import validate_connection_metadata


def _as_board_dict(board_cfg: Any) -> Dict[str, Any]:
    """
    Coerce a board_cfg value to a plain dict.

    Accepts:
    - A plain dict (returned as-is)
    - A DUTConfig (or any object with to_legacy_dict()) — calls to_legacy_dict()
    - Anything else — returns {}

    This allows connection_model to work with both the old raw-dict path
    (strategy_resolver / pipeline) and the new DUTConfig path (inventory).
    """
    if isinstance(board_cfg, dict):
        return board_cfg
    if hasattr(board_cfg, "to_legacy_dict") and callable(board_cfg.to_legacy_dict):
        return board_cfg.to_legacy_dict()
    return {}


class SetupComponentStatus(str, Enum):
    VERIFIED = "verified"                                    # confirmed by discovery or prior run
    PROVISIONED_UNVERIFIED = "provisioned_unverified"        # wired but not auto-confirmed
    DEFINED_NOT_PROVISIONED = "defined_not_provisioned"      # in config, not yet wired
    MANUALLY_UNSPECIFIED = "manually_unspecified"            # manual step required, status unknown
    NOT_APPLICABLE = "not_applicable"


@dataclass
class SetupComponentEntry:
    component_type: str          # "instrument_role", "external_input", "dut_to_instrument"
    component_id: str            # role name or source name
    status: SetupComponentStatus
    required: bool
    notes: str = ""


@dataclass
class SetupReadinessSummary:
    overall: SetupComponentStatus          # worst-case rollup across required components
    components: List[SetupComponentEntry]
    blocking_issues: List[str]             # human-readable list of what blocks execution
    warnings: List[str]                    # non-blocking issues
    ready_to_run: bool                     # True only if all required components are VERIFIED or PROVISIONED_UNVERIFIED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall.value,
            "ready_to_run": self.ready_to_run,
            "blocking_issues": list(self.blocking_issues),
            "warnings": list(self.warnings),
            "components": [
                {
                    "component_type": c.component_type,
                    "component_id": c.component_id,
                    "status": c.status.value,
                    "required": c.required,
                    "notes": c.notes,
                }
                for c in self.components
            ],
        }


_STATUS_MAP: Dict[str, SetupComponentStatus] = {
    "manual_loopback_required": SetupComponentStatus.MANUALLY_UNSPECIFIED,
    "defined_not_provisioned": SetupComponentStatus.DEFINED_NOT_PROVISIONED,
    "provisioned": SetupComponentStatus.PROVISIONED_UNVERIFIED,
    "verified": SetupComponentStatus.VERIFIED,
}


def build_setup_readiness(bench_setup: Dict[str, Any]) -> SetupReadinessSummary:
    """Build a SetupReadinessSummary from a bench_setup dict.

    Maps existing status strings from external_inputs / instrument_roles to
    SetupComponentStatus enum values and computes a worst-case rollup.
    """
    if not isinstance(bench_setup, dict):
        return SetupReadinessSummary(
            overall=SetupComponentStatus.NOT_APPLICABLE,
            components=[],
            blocking_issues=[],
            warnings=[],
            ready_to_run=True,
        )

    components: List[SetupComponentEntry] = []

    for role in bench_setup.get("instrument_roles", []) or []:
        if not isinstance(role, dict):
            continue
        status_str = str(role.get("status") or "provisioned")
        components.append(SetupComponentEntry(
            component_type="instrument_role",
            component_id=str(role.get("role") or "unknown"),
            status=_STATUS_MAP.get(status_str, SetupComponentStatus.PROVISIONED_UNVERIFIED),
            required=bool(role.get("required", True)),
            notes=str(role.get("notes") or ""),
        ))

    for ext in bench_setup.get("external_inputs", []) or []:
        if not isinstance(ext, dict):
            continue
        status_str = str(ext.get("status") or "defined_not_provisioned")
        components.append(SetupComponentEntry(
            component_type="external_input",
            component_id=str(ext.get("source") or "unknown"),
            status=_STATUS_MAP.get(status_str, SetupComponentStatus.DEFINED_NOT_PROVISIONED),
            required=bool(ext.get("required", True)),
            notes=str(ext.get("notes") or ""),
        ))

    for conn in bench_setup.get("dut_to_instrument", []) or []:
        if not isinstance(conn, dict):
            continue
        components.append(SetupComponentEntry(
            component_type="dut_to_instrument",
            component_id=str(conn.get("dut_gpio") or "unknown"),
            status=SetupComponentStatus.PROVISIONED_UNVERIFIED,
            required=True,
        ))

    _blocking_statuses = {
        SetupComponentStatus.DEFINED_NOT_PROVISIONED,
        SetupComponentStatus.MANUALLY_UNSPECIFIED,
    }
    blocking = [
        f"{c.component_type} '{c.component_id}': {c.status.value}"
        for c in components
        if c.required and c.status in _blocking_statuses
    ]

    required_statuses = [c.status for c in components if c.required]
    if not required_statuses:
        overall = SetupComponentStatus.NOT_APPLICABLE
    elif SetupComponentStatus.MANUALLY_UNSPECIFIED in required_statuses:
        overall = SetupComponentStatus.MANUALLY_UNSPECIFIED
    elif SetupComponentStatus.DEFINED_NOT_PROVISIONED in required_statuses:
        overall = SetupComponentStatus.DEFINED_NOT_PROVISIONED
    elif SetupComponentStatus.PROVISIONED_UNVERIFIED in required_statuses:
        overall = SetupComponentStatus.PROVISIONED_UNVERIFIED
    else:
        overall = SetupComponentStatus.VERIFIED

    return SetupReadinessSummary(
        overall=overall,
        components=components,
        blocking_issues=blocking,
        warnings=[],
        ready_to_run=len(blocking) == 0,
    )


@dataclass(frozen=True)
class NormalizedConnectionContext:
    default_wiring: Dict[str, str]
    resolved_wiring: Dict[str, str]
    bench_connections: List[Dict[str, Any]]
    bench_setup: Dict[str, Any]
    observe_map: Dict[str, Any]
    verification_views: Dict[str, Any]
    warnings: List[str]
    validation_errors: List[str]
    source_summary: Dict[str, Any]
    setup_readiness: Optional[SetupReadinessSummary] = None


def parse_wiring_override(wiring: Optional[str]) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    if not wiring:
        return parsed
    parts = [p.strip() for p in str(wiring).split() if p.strip()]
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            parsed[key] = value
    return parsed


def resolve_bench_setup(test_raw: Dict[str, Any] | Any) -> Dict[str, Any]:
    if not isinstance(test_raw, dict):
        return {}
    bench_setup = test_raw.get("bench_setup")
    if isinstance(bench_setup, dict) and bench_setup:
        return dict(bench_setup)
    legacy = test_raw.get("connections")
    if isinstance(legacy, dict):
        return dict(legacy)
    if isinstance(bench_setup, dict):
        return dict(bench_setup)
    return {}


def _normalize_mapping(raw: Dict[str, Any] | Any) -> Dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _normalize_list_of_mappings(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, dict)]


def _semantic_connection_warnings(
    *,
    board: Dict[str, Any],
    test: Dict[str, Any],
    resolved_wiring: Dict[str, Any],
    observe_map: Dict[str, Any],
    verification_views: Dict[str, Any],
) -> List[str]:
    warnings: List[str] = []

    verify_target = str((resolved_wiring or {}).get("verify") or "").strip()
    sig_target = str((observe_map or {}).get("sig") or "").strip()
    if verify_target and verify_target != "UNKNOWN" and sig_target and verify_target != sig_target:
        warnings.append(
            f"verify wiring resolves to {verify_target}, but observe_map.sig resolves to {sig_target}"
        )

    if isinstance(verification_views, dict):
        for view_name, raw_view in verification_views.items():
            if not isinstance(raw_view, dict):
                continue
            pin = str(raw_view.get("pin") or "").strip()
            resolved_to = str(raw_view.get("resolved_to") or "").strip()
            if not pin or not resolved_to:
                continue
            observed = str((observe_map or {}).get(pin) or "").strip()
            if observed and observed != resolved_to:
                warnings.append(
                    f"verification view {view_name} resolves {pin} to {resolved_to}, but observe_map[{pin}] resolves to {observed}"
                )

    pin_label = str((test or {}).get("pin") or "").strip()
    if pin_label:
        resolved_pin = str((observe_map or {}).get(pin_label) or "").strip()
        if not resolved_pin and pin_label == "sig":
            resolved_pin = sig_target
        signal_view = verification_views.get("signal") if isinstance(verification_views, dict) else None
        signal_target = ""
        if isinstance(signal_view, dict):
            signal_target = str(signal_view.get("resolved_to") or "").strip()
        if resolved_pin and signal_target and resolved_pin != signal_target:
            warnings.append(
                f"test pin {pin_label} resolves to {resolved_pin}, but verification_views.signal resolves to {signal_target}"
            )

    bench_connections = _normalize_list_of_mappings(board.get("bench_connections"))
    if bench_connections and isinstance(verification_views, dict):
        by_target = {str(item.get("to") or "").strip() for item in bench_connections if str(item.get("to") or "").strip()}
        for view_name, raw_view in verification_views.items():
            if not isinstance(raw_view, dict):
                continue
            resolved_to = str(raw_view.get("resolved_to") or "").strip()
            if resolved_to and resolved_to not in by_target and resolved_to != "LED":
                warnings.append(
                    f"verification view {view_name} resolves to {resolved_to}, but bench_connections do not mention that observation point"
                )

    return warnings


def _semantic_validation_errors(
    *,
    test: Dict[str, Any],
    observe_map: Dict[str, Any],
    verification_views: Dict[str, Any],
) -> List[str]:
    errors: List[str] = []
    pin_label = str((test or {}).get("pin") or "").strip()
    if not pin_label:
        return errors
    resolved_pin = str((observe_map or {}).get(pin_label) or "").strip()
    signal_view = verification_views.get("signal") if isinstance(verification_views, dict) else None
    signal_target = ""
    if isinstance(signal_view, dict):
        signal_target = str(signal_view.get("resolved_to") or "").strip()
    if not resolved_pin and pin_label == "sig":
        resolved_pin = str((observe_map or {}).get("sig") or "").strip()
    if not resolved_pin and not signal_target:
        errors.append(f"signal test pin {pin_label} has no resolved observation target")
    return errors


def merge_wiring(defaults: Dict[str, Any] | Any, overrides: Dict[str, Any] | Any, required: List[str] | None = None) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    for source in (defaults, overrides):
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            k = str(key).strip()
            v = str(value).strip() if value is not None else ""
            if k and v:
                merged[k] = v
    for key in required or []:
        if not merged.get(key):
            merged[key] = "UNKNOWN"
    return merged


def connection_warnings(
    board_cfg: Dict[str, Any] | Any,
    test_raw: Dict[str, Any] | Any,
    resolved_wiring: Dict[str, Any] | Any,
) -> List[str]:
    warnings: List[str] = []
    board = _as_board_dict(board_cfg)
    test = test_raw if isinstance(test_raw, dict) else {}

    missing = [key for key in ("swd", "reset", "verify") if str((resolved_wiring or {}).get(key) or "").strip() == "UNKNOWN"]
    if missing:
        warnings.append(f"missing coarse wiring: {', '.join(missing)}")

    bench_connections = _normalize_list_of_mappings(board.get("bench_connections"))
    observe_map = _normalize_mapping(board.get("observe_map"))
    verification_views = _normalize_mapping(board.get("verification_views"))
    from_counts: Counter[str] = Counter()
    for item in bench_connections:
        src = str(item.get("from") or "").strip()
        if src:
            from_counts[src] += 1
    for src, count in sorted(from_counts.items()):
        if count > 1:
            warnings.append(
                f"MCU pin {src} is connected to {count} observation points; verify signal loading, shared ground, and whether the instrument supports parallel observation on that net."
            )

    bench_setup = resolve_bench_setup(test)
    if isinstance(test.get("instrument"), dict) and not bench_setup:
        warnings.append("instrument test has no bench_setup or legacy connections block")
    if bench_setup.get("ground_required") and bench_setup.get("ground_confirmed") is not True:
        warnings.append("bench_setup requires ground, but ground_confirmed is not true")
    if str((resolved_wiring or {}).get("verify") or "").strip() == "UNKNOWN":
        if not observe_map:
            warnings.append("verify mapping is ambiguous because observe_map is missing")
    warnings.extend(
        _semantic_connection_warnings(
            board=board,
            test=test,
            resolved_wiring=_normalize_mapping(resolved_wiring),
            observe_map=observe_map,
            verification_views=verification_views,
        )
    )
    return warnings


def normalize_connection_context(
    board_cfg: Dict[str, Any] | Any,
    test_raw: Dict[str, Any] | Any,
    wiring: Optional[str] = None,
    *,
    required_wiring: List[str] | None = None,
) -> NormalizedConnectionContext:
    board = _as_board_dict(board_cfg)
    defaults = _normalize_mapping(board.get("default_wiring"))
    overrides = parse_wiring_override(wiring)
    resolved_wiring = merge_wiring(defaults, overrides, required=required_wiring or [])
    bench_setup = resolve_bench_setup(test_raw)
    bench_connections = _normalize_list_of_mappings(board.get("bench_connections"))
    observe_map = _normalize_mapping(board.get("observe_map"))
    verification_views = _normalize_mapping(board.get("verification_views"))
    warnings = connection_warnings(board, test_raw, resolved_wiring)
    validation_errors = validate_connection_metadata(board, test_raw)
    validation_errors.extend(
        _semantic_validation_errors(
            test=test_raw if isinstance(test_raw, dict) else {},
            observe_map=observe_map,
            verification_views=verification_views,
        )
    )
    return NormalizedConnectionContext(
        default_wiring=defaults,
        resolved_wiring=resolved_wiring,
        bench_connections=bench_connections,
        bench_setup=bench_setup,
        observe_map=observe_map,
        verification_views=verification_views,
        warnings=warnings,
        validation_errors=validation_errors,
        source_summary={
            "default_wiring": "board.default_wiring" if defaults else None,
            "bench_connections": "board.bench_connections" if bench_connections else None,
            "bench_setup": (
                "test.bench_setup"
                if isinstance(test_raw, dict) and isinstance(test_raw.get("bench_setup"), dict) and test_raw.get("bench_setup")
                else "test.connections" if bench_setup else None
            ),
            "wiring_override": "cli.wiring" if overrides else None,
        },
        setup_readiness=build_setup_readiness(bench_setup),
    )


def build_connection_rows(ctx: NormalizedConnectionContext, test_raw: Dict[str, Any] | Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    test = test_raw if isinstance(test_raw, dict) else {}
    bench_setup = ctx.bench_setup if isinstance(ctx.bench_setup, dict) else {}
    bench_rows: List[Dict[str, Any]] = []
    if isinstance(test.get("instrument"), dict) or bench_setup:
        for item in bench_setup.get("dut_to_instrument", []) if isinstance(bench_setup.get("dut_to_instrument"), list) else []:
            if not isinstance(item, dict):
                continue
            row = {
                "from": item.get("dut_gpio"),
                "to": f"inst GPIO{item.get('inst_gpio')}",
                "expect": item.get("expect"),
            }
            if item.get("freq_hz") is not None:
                row["freq_hz"] = item.get("freq_hz")
            bench_rows.append(row)
        for item in bench_setup.get("dut_to_instrument_analog", []) if isinstance(bench_setup.get("dut_to_instrument_analog"), list) else []:
            if not isinstance(item, dict):
                continue
            row = {
                "from": item.get("dut_signal"),
                "to": f"inst ADC GPIO{item.get('inst_adc_gpio')}",
                "expect_v_min": item.get("expect_v_min"),
                "expect_v_max": item.get("expect_v_max"),
            }
            if item.get("avg") is not None:
                row["avg"] = item.get("avg")
            bench_rows.append(row)
        for item in bench_setup.get("external_inputs", []) if isinstance(bench_setup.get("external_inputs"), list) else []:
            if not isinstance(item, dict):
                continue
            row = {
                "from": item.get("source") or "external source",
                "to": item.get("dut_signal"),
                "kind": item.get("kind"),
            }
            if item.get("required") is not None:
                row["required"] = item.get("required")
            if item.get("status"):
                row["status"] = item.get("status")
            if item.get("notes"):
                row["notes"] = item.get("notes")
            bench_rows.append(row)
        for item in bench_setup.get("peripheral_signals", []) if isinstance(bench_setup.get("peripheral_signals"), list) else []:
            if not isinstance(item, dict):
                continue
            row = {
                "from": item.get("role"),
                "to": item.get("dut_signal"),
                "kind": "peripheral_signal",
            }
            if item.get("direction"):
                row["direction"] = item.get("direction")
            if item.get("notes"):
                row["notes"] = item.get("notes")
            bench_rows.append(row)
        serial_console = bench_setup.get("serial_console")
        if isinstance(serial_console, dict):
            row = {
                "from": "host serial",
                "to": serial_console.get("port"),
                "kind": "serial_console",
            }
            if serial_console.get("baud") is not None:
                row["baud"] = serial_console.get("baud")
            bench_rows.append(row)
        for item in bench_setup.get("instrument_roles", []) if isinstance(bench_setup.get("instrument_roles"), list) else []:
            if not isinstance(item, dict):
                continue
            row = {
                "from": item.get("role"),
                "to": item.get("instrument_id"),
                "kind": "instrument_role",
            }
            if item.get("required") is not None:
                row["required"] = item.get("required")
            if item.get("endpoint"):
                row["endpoint"] = item.get("endpoint")
            if item.get("notes"):
                row["notes"] = item.get("notes")
            bench_rows.append(row)
        if bench_setup.get("ground_required"):
            bench_rows.append({"from": "GND", "to": "inst GND", "required": True})
        if isinstance(test.get("instrument"), dict) and bench_rows:
            return bench_rows

    if ctx.resolved_wiring.get("swd"):
        rows.append({"from": "SWD", "to": ctx.resolved_wiring.get("swd")})
    if "reset" in ctx.resolved_wiring:
        rows.append({"from": "RESET", "to": ctx.resolved_wiring.get("reset")})
    for item in ctx.bench_connections:
        src = item.get("from")
        dst = item.get("to")
        if src and dst:
            rows.append({"from": src, "to": dst})
    if rows and len(rows) > 2:
        if bench_rows:
            rows.extend(bench_rows)
        return rows
    pin = test.get("pin")
    if pin:
        resolved = ctx.observe_map.get(str(pin), ctx.resolved_wiring.get("verify"))
        observed_label = str(pin)
        if observed_label == "sig":
            for key, value in ctx.observe_map.items():
                if key != "sig" and value == ctx.observe_map.get("sig"):
                    observed_label = key.upper() if key.startswith(("pa", "pb", "pc")) else str(key)
                    break
        rows.append({"from": observed_label, "to": resolved})
    if bench_rows:
        rows.extend(bench_rows)
    return rows


def wiring_assumption_lines(ctx: NormalizedConnectionContext) -> List[str]:
    lines: List[str] = []
    bench_setup = ctx.bench_setup if isinstance(ctx.bench_setup, dict) else {}
    for item in bench_setup.get("dut_to_instrument", []) if isinstance(bench_setup.get("dut_to_instrument"), list) else []:
        if not isinstance(item, dict):
            continue
        line = f"{item.get('dut_gpio')} -> GPIO{item.get('inst_gpio')} {item.get('expect')}"
        if item.get("freq_hz"):
            line += f" @{item.get('freq_hz')}Hz"
        lines.append(line)
    for item in bench_setup.get("dut_to_instrument_analog", []) if isinstance(bench_setup.get("dut_to_instrument_analog"), list) else []:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"{item.get('dut_signal')} -> ADC GPIO{item.get('inst_adc_gpio')} "
            f"{item.get('expect_v_min')}V..{item.get('expect_v_max')}V"
        )
    for item in bench_setup.get("external_inputs", []) if isinstance(bench_setup.get("external_inputs"), list) else []:
        if not isinstance(item, dict):
            continue
        line = f"{item.get('source') or 'external source'} -> {item.get('dut_signal')}"
        if item.get("kind"):
            line += f" kind={item.get('kind')}"
        if item.get("status"):
            line += f" status={item.get('status')}"
        lines.append(line)
    for item in bench_setup.get("peripheral_signals", []) if isinstance(bench_setup.get("peripheral_signals"), list) else []:
        if not isinstance(item, dict):
            continue
        line = f"{item.get('role')} -> {item.get('dut_signal')}"
        if item.get("direction"):
            line += f" direction={item.get('direction')}"
        lines.append(line)
    serial_console = bench_setup.get("serial_console")
    if isinstance(serial_console, dict):
        lines.append(
            f"host serial -> {serial_console.get('port')} baud={serial_console.get('baud')}"
        )
    for item in bench_setup.get("instrument_roles", []) if isinstance(bench_setup.get("instrument_roles"), list) else []:
        if not isinstance(item, dict):
            continue
        line = f"{item.get('role')} -> {item.get('instrument_id')}"
        if item.get("endpoint"):
            line += f" endpoint={item.get('endpoint')}"
        if item.get("required") is not None:
            line += f" required={item.get('required')}"
        lines.append(line)
    if bench_setup.get("ground_required"):
        lines.append("GND -> GND")
    return lines


def build_connection_setup(ctx: NormalizedConnectionContext) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "resolved_wiring": dict(ctx.resolved_wiring),
        "default_wiring": dict(ctx.default_wiring),
        "bench_connections": [dict(item) for item in ctx.bench_connections],
        "bench_setup": dict(ctx.bench_setup),
        "observe_map": dict(ctx.observe_map),
        "verification_views": dict(ctx.verification_views),
        "warnings": list(ctx.warnings),
        "validation_errors": list(ctx.validation_errors),
        "source_summary": dict(ctx.source_summary),
    }
    if ctx.setup_readiness is not None:
        result["setup_readiness"] = ctx.setup_readiness.to_dict()
    return result


def render_connection_setup_text(connection_setup: Dict[str, Any] | Any, *, indent: str = "") -> List[str]:
    setup = connection_setup if isinstance(connection_setup, dict) else {}
    lines: List[str] = []

    source_summary = setup.get("source_summary")
    if isinstance(source_summary, dict) and source_summary:
        lines.append(f"{indent}source_summary:")
        for key, value in source_summary.items():
            if value:
                lines.append(f"{indent}  - {key}: {value}")

    resolved_wiring = setup.get("resolved_wiring")
    if isinstance(resolved_wiring, dict) and resolved_wiring:
        lines.append(f"{indent}resolved_wiring:")
        for key, value in resolved_wiring.items():
            lines.append(f"{indent}  - {key}: {value}")

    verification_views = setup.get("verification_views")
    if isinstance(verification_views, dict) and verification_views:
        lines.append(f"{indent}verification_views:")
        for name, view in verification_views.items():
            if isinstance(view, dict):
                pin = view.get("pin")
                resolved_to = view.get("resolved_to")
                if pin or resolved_to:
                    lines.append(f"{indent}  - {name}: pin={pin} resolved_to={resolved_to}")
                else:
                    lines.append(f"{indent}  - {name}: {view}")
            else:
                lines.append(f"{indent}  - {name}: {view}")

    bench_connections = setup.get("bench_connections")
    if isinstance(bench_connections, list) and bench_connections:
        lines.append(f"{indent}bench_connections:")
        for item in bench_connections:
            if not isinstance(item, dict):
                continue
            src = item.get("from")
            dst = item.get("to")
            if src or dst:
                lines.append(f"{indent}  - {src} -> {dst}")
            else:
                lines.append(f"{indent}  - {item}")

    bench_setup = setup.get("bench_setup")
    if isinstance(bench_setup, dict) and bench_setup:
        lines.append(f"{indent}bench_setup:")
        for item in bench_setup.get("dut_to_instrument", []) if isinstance(bench_setup.get("dut_to_instrument"), list) else []:
            if not isinstance(item, dict):
                continue
            line = f"{item.get('dut_gpio')} -> inst GPIO{item.get('inst_gpio')}"
            if item.get("expect"):
                line += f" expect={item.get('expect')}"
            if item.get("freq_hz") is not None:
                line += f" freq_hz={item.get('freq_hz')}"
            lines.append(f"{indent}  - {line}")
        for item in bench_setup.get("dut_to_instrument_analog", []) if isinstance(bench_setup.get("dut_to_instrument_analog"), list) else []:
            if not isinstance(item, dict):
                continue
            line = (
                f"{item.get('dut_signal')} -> inst ADC GPIO{item.get('inst_adc_gpio')} "
                f"expect_v={item.get('expect_v_min')}..{item.get('expect_v_max')}"
            )
            lines.append(f"{indent}  - {line}")
        serial_console = bench_setup.get("serial_console")
        if isinstance(serial_console, dict):
            lines.append(
                f"{indent}  - host serial -> {serial_console.get('port')} baud={serial_console.get('baud')}"
            )
        for item in bench_setup.get("instrument_roles", []) if isinstance(bench_setup.get("instrument_roles"), list) else []:
            if not isinstance(item, dict):
                continue
            line = f"{item.get('role')} -> {item.get('instrument_id')}"
            if item.get("endpoint"):
                line += f" endpoint={item.get('endpoint')}"
            if item.get("required") is not None:
                line += f" required={item.get('required')}"
            if item.get("notes"):
                line += f" notes={item.get('notes')}"
            lines.append(f"{indent}  - {line}")
        for item in bench_setup.get("external_inputs", []) if isinstance(bench_setup.get("external_inputs"), list) else []:
            if not isinstance(item, dict):
                continue
            line = f"{item.get('source') or 'external source'} -> {item.get('dut_signal')} kind={item.get('kind')}"
            if item.get("status"):
                line += f" status={item.get('status')}"
            if item.get("notes"):
                line += f" notes={item.get('notes')}"
            lines.append(f"{indent}  - {line}")
        for item in bench_setup.get("peripheral_signals", []) if isinstance(bench_setup.get("peripheral_signals"), list) else []:
            if not isinstance(item, dict):
                continue
            line = f"{item.get('role')} -> {item.get('dut_signal')}"
            if item.get("direction"):
                line += f" direction={item.get('direction')}"
            if item.get("notes"):
                line += f" notes={item.get('notes')}"
            lines.append(f"{indent}  - {line}")
        if bench_setup.get("ground_required") is not None:
            lines.append(f"{indent}  - ground_required: {bench_setup.get('ground_required')}")
        if "ground_confirmed" in bench_setup:
            lines.append(f"{indent}  - ground_confirmed: {bench_setup.get('ground_confirmed')}")

    warnings = setup.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines.append(f"{indent}warnings:")
        for item in warnings:
            lines.append(f"{indent}  - {item}")

    validation_errors = setup.get("validation_errors")
    if isinstance(validation_errors, list) and validation_errors:
        lines.append(f"{indent}validation_errors:")
        for item in validation_errors:
            lines.append(f"{indent}  - {item}")

    return lines


def build_connection_digest(connection_setup: Dict[str, Any] | Any) -> List[str]:
    setup = connection_setup if isinstance(connection_setup, dict) else {}
    digest: List[str] = []

    resolved_wiring = setup.get("resolved_wiring")
    if isinstance(resolved_wiring, dict):
        parts = []
        for key in ("swd", "reset", "verify"):
            value = str(resolved_wiring.get(key) or "").strip()
            if value:
                parts.append(f"{key}={value}")
        if parts:
            digest.append("wiring: " + ", ".join(parts))

    verification_views = setup.get("verification_views")
    if isinstance(verification_views, dict):
        for name, view in verification_views.items():
            if not isinstance(view, dict):
                continue
            pin = str(view.get("pin") or "").strip()
            resolved_to = str(view.get("resolved_to") or "").strip()
            if pin and resolved_to:
                digest.append(f"view {name}: {pin}->{resolved_to}")

    bench_connections = setup.get("bench_connections")
    if isinstance(bench_connections, list):
        for item in bench_connections:
            if not isinstance(item, dict):
                continue
            src = str(item.get("from") or "").strip()
            dst = str(item.get("to") or "").strip()
            if src and dst:
                digest.append(f"net {src}->{dst}")

    bench_setup = setup.get("bench_setup")
    if isinstance(bench_setup, dict):
        for item in bench_setup.get("dut_to_instrument", []) if isinstance(bench_setup.get("dut_to_instrument"), list) else []:
            if not isinstance(item, dict):
                continue
            src = str(item.get("dut_gpio") or "").strip()
            dst = str(item.get("inst_gpio") or "").strip()
            if src and dst:
                digest.append(f"digital {src}->GPIO{dst}")
        for item in bench_setup.get("dut_to_instrument_analog", []) if isinstance(bench_setup.get("dut_to_instrument_analog"), list) else []:
            if not isinstance(item, dict):
                continue
            src = str(item.get("dut_signal") or "").strip()
            dst = str(item.get("inst_adc_gpio") or "").strip()
            if src and dst:
                digest.append(f"analog {src}->ADC{dst}")
        serial_console = bench_setup.get("serial_console")
        if isinstance(serial_console, dict):
            port = str(serial_console.get("port") or "").strip()
            baud = str(serial_console.get("baud") or "").strip()
            if port and baud:
                digest.append(f"serial {port}@{baud}")
        for item in bench_setup.get("instrument_roles", []) if isinstance(bench_setup.get("instrument_roles"), list) else []:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip()
            instrument_id = str(item.get("instrument_id") or "").strip()
            if role and instrument_id:
                digest.append(f"instrument_role {role}->{instrument_id}")
        for item in bench_setup.get("external_inputs", []) if isinstance(bench_setup.get("external_inputs"), list) else []:
            if not isinstance(item, dict):
                continue
            src = str(item.get("source") or "").strip() or "external source"
            dst = str(item.get("dut_signal") or "").strip()
            kind = str(item.get("kind") or "").strip()
            if dst:
                digest.append(f"external {src}->{dst}:{kind}")
        for item in bench_setup.get("peripheral_signals", []) if isinstance(bench_setup.get("peripheral_signals"), list) else []:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip()
            dst = str(item.get("dut_signal") or "").strip()
            if role and dst:
                digest.append(f"peripheral {role}->{dst}")
        if bench_setup.get("ground_required") is True:
            ground_confirmed = bench_setup.get("ground_confirmed")
            digest.append(f"ground required confirmed={ground_confirmed}")

    warnings = setup.get("warnings")
    if isinstance(warnings, list):
        for item in warnings:
            digest.append(f"warning {item}")

    validation_errors = setup.get("validation_errors")
    if isinstance(validation_errors, list):
        for item in validation_errors:
            digest.append(f"validation_error {item}")

    return digest


def diff_connection_setups(
    left: Dict[str, Any] | Any,
    right: Dict[str, Any] | Any,
    *,
    left_label: str = "left",
    right_label: str = "right",
) -> Dict[str, Any]:
    left_setup = left if isinstance(left, dict) else {}
    right_setup = right if isinstance(right, dict) else {}
    left_digest = build_connection_digest(left_setup)
    right_digest = build_connection_digest(right_setup)
    left_only = [item for item in left_digest if item not in right_digest]
    right_only = [item for item in right_digest if item not in left_digest]
    return {
        "ok": True,
        "left_label": left_label,
        "right_label": right_label,
        "left_only": left_only,
        "right_only": right_only,
        "same": not left_only and not right_only,
    }
