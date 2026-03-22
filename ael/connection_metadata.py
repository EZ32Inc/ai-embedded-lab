from __future__ import annotations

from typing import Any, Dict, List


def _is_bool_like(value: Any) -> bool:
    return isinstance(value, bool)


def validate_default_wiring(raw: Dict[str, Any] | Any) -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, dict):
        return ["default_wiring must be a mapping"]
    errors: List[str] = []
    for key, value in raw.items():
        name = str(key or "").strip()
        if not name:
            errors.append("default_wiring contains an empty key")
            continue
        if not str(value or "").strip():
            errors.append(f"default_wiring[{name}] must be a non-empty string")
    return errors


def validate_bench_connections(raw: Any) -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        return ["bench_connections must be a list"]
    errors: List[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"bench_connections[{index}] must be a mapping")
            continue
        if not str(item.get("from") or "").strip():
            errors.append(f"bench_connections[{index}].from is required")
        if not str(item.get("to") or "").strip():
            errors.append(f"bench_connections[{index}].to is required")
    return errors


def validate_observe_map(raw: Dict[str, Any] | Any) -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, dict):
        return ["observe_map must be a mapping"]
    errors: List[str] = []
    for key, value in raw.items():
        name = str(key or "").strip()
        if not name:
            errors.append("observe_map contains an empty key")
            continue
        if not str(value or "").strip():
            errors.append(f"observe_map[{name}] must be a non-empty string")
    return errors


def validate_verification_views(raw: Dict[str, Any] | Any) -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, dict):
        return ["verification_views must be a mapping"]
    errors: List[str] = []
    for name, item in raw.items():
        view = str(name or "").strip()
        if not view:
            errors.append("verification_views contains an empty key")
            continue
        if not isinstance(item, dict):
            errors.append(f"verification_views[{view}] must be a mapping")
            continue
        if not str(item.get("pin") or "").strip():
            errors.append(f"verification_views[{view}].pin is required")
        if not str(item.get("resolved_to") or "").strip():
            errors.append(f"verification_views[{view}].resolved_to is required")
    return errors


def validate_bench_setup(raw: Dict[str, Any] | Any, *, source_name: str = "bench_setup") -> List[str]:
    if raw is None:
        return []
    if not isinstance(raw, dict):
        return [f"{source_name} must be a mapping"]
    errors: List[str] = []
    digital = raw.get("dut_to_instrument")
    if digital is not None:
        if not isinstance(digital, list):
            errors.append(f"{source_name}.dut_to_instrument must be a list")
        else:
            for index, item in enumerate(digital):
                if not isinstance(item, dict):
                    errors.append(f"{source_name}.dut_to_instrument[{index}] must be a mapping")
                    continue
                if not str(item.get("dut_gpio") or "").strip():
                    errors.append(f"{source_name}.dut_to_instrument[{index}].dut_gpio is required")
                if item.get("inst_gpio") is None or not str(item.get("inst_gpio")).strip():
                    errors.append(f"{source_name}.dut_to_instrument[{index}].inst_gpio is required")
    analog = raw.get("dut_to_instrument_analog")
    if analog is not None:
        if not isinstance(analog, list):
            errors.append(f"{source_name}.dut_to_instrument_analog must be a list")
        else:
            for index, item in enumerate(analog):
                if not isinstance(item, dict):
                    errors.append(f"{source_name}.dut_to_instrument_analog[{index}] must be a mapping")
                    continue
                if not str(item.get("dut_signal") or "").strip():
                    errors.append(f"{source_name}.dut_to_instrument_analog[{index}].dut_signal is required")
                if item.get("inst_adc_gpio") is None or not str(item.get("inst_adc_gpio")).strip():
                    errors.append(f"{source_name}.dut_to_instrument_analog[{index}].inst_adc_gpio is required")
    serial_console = raw.get("serial_console")
    if serial_console is not None:
        if not isinstance(serial_console, dict):
            errors.append(f"{source_name}.serial_console must be a mapping")
        else:
            if not str(serial_console.get("port") or "").strip():
                errors.append(f"{source_name}.serial_console.port is required")
            if serial_console.get("baud") is None or not str(serial_console.get("baud")).strip():
                errors.append(f"{source_name}.serial_console.baud is required")
    instrument_roles = raw.get("instrument_roles")
    if instrument_roles is not None:
        if not isinstance(instrument_roles, list):
            errors.append(f"{source_name}.instrument_roles must be a list")
        else:
            for index, item in enumerate(instrument_roles):
                if not isinstance(item, dict):
                    errors.append(f"{source_name}.instrument_roles[{index}] must be a mapping")
                    continue
                if not str(item.get("role") or "").strip():
                    errors.append(f"{source_name}.instrument_roles[{index}].role is required")
                if not str(item.get("instrument_id") or "").strip():
                    errors.append(f"{source_name}.instrument_roles[{index}].instrument_id is required")
                if "required" in item and not _is_bool_like(item.get("required")):
                    errors.append(f"{source_name}.instrument_roles[{index}].required must be a boolean")
    external_inputs = raw.get("external_inputs")
    if external_inputs is not None:
        if not isinstance(external_inputs, list):
            errors.append(f"{source_name}.external_inputs must be a list")
        else:
            for index, item in enumerate(external_inputs):
                if not isinstance(item, dict):
                    errors.append(f"{source_name}.external_inputs[{index}] must be a mapping")
                    continue
                if not str(item.get("dut_signal") or "").strip():
                    errors.append(f"{source_name}.external_inputs[{index}].dut_signal is required")
                if not str(item.get("kind") or "").strip():
                    errors.append(f"{source_name}.external_inputs[{index}].kind is required")
                if "required" in item and not _is_bool_like(item.get("required")):
                    errors.append(f"{source_name}.external_inputs[{index}].required must be a boolean")
    peripheral_signals = raw.get("peripheral_signals")
    if peripheral_signals is not None:
        if not isinstance(peripheral_signals, list):
            errors.append(f"{source_name}.peripheral_signals must be a list")
        else:
            for index, item in enumerate(peripheral_signals):
                if not isinstance(item, dict):
                    errors.append(f"{source_name}.peripheral_signals[{index}] must be a mapping")
                    continue
                if not str(item.get("role") or "").strip():
                    errors.append(f"{source_name}.peripheral_signals[{index}].role is required")
                if not str(item.get("dut_signal") or "").strip():
                    errors.append(f"{source_name}.peripheral_signals[{index}].dut_signal is required")
    if "ground_required" in raw and not _is_bool_like(raw.get("ground_required")):
        errors.append(f"{source_name}.ground_required must be a boolean")
    if "ground_confirmed" in raw and not _is_bool_like(raw.get("ground_confirmed")):
        errors.append(f"{source_name}.ground_confirmed must be a boolean")
    return errors


VALID_RESET_STRATEGIES = {"connect_under_reset", "pulse_reset", "none"}
VALID_BOOT_MODES = {"normal", "bootloader", "isp"}


def validate_power_and_boot(power_and_boot: Dict[str, Any] | Any) -> List[str]:
    """Validate the optional power_and_boot section in a board config."""
    if power_and_boot is None:
        return []
    if not isinstance(power_and_boot, dict):
        return ["power_and_boot must be a mapping"]
    errors: List[str] = []
    strategy = power_and_boot.get("reset_strategy")
    if strategy is not None and str(strategy) not in VALID_RESET_STRATEGIES:
        errors.append(f"power_and_boot.reset_strategy '{strategy}' not in {sorted(VALID_RESET_STRATEGIES)}")
    boot_mode = power_and_boot.get("boot_mode_default")
    if boot_mode is not None and str(boot_mode) not in VALID_BOOT_MODES:
        errors.append(f"power_and_boot.boot_mode_default '{boot_mode}' not in {sorted(VALID_BOOT_MODES)}")
    for index, rail in enumerate(power_and_boot.get("power_rails", []) or []):
        if not isinstance(rail, dict):
            errors.append(f"power_and_boot.power_rails[{index}] must be a mapping")
            continue
        if not str(rail.get("name") or "").strip():
            errors.append(f"power_and_boot.power_rails[{index}].name is required")
        if rail.get("nominal_v") is None:
            errors.append(f"power_and_boot.power_rails[{index}].nominal_v is required")
    return errors


def validate_connection_metadata(
    board_cfg: Dict[str, Any] | Any,
    test_raw: Dict[str, Any] | Any,
) -> List[str]:
    if hasattr(board_cfg, "to_legacy_dict"):
        board = board_cfg.to_legacy_dict()
    elif isinstance(board_cfg, dict):
        board = board_cfg
    else:
        board = {}
    test = test_raw if isinstance(test_raw, dict) else {}
    errors: List[str] = []
    errors.extend(validate_default_wiring(board.get("default_wiring")))
    errors.extend(validate_bench_connections(board.get("bench_connections")))
    errors.extend(validate_observe_map(board.get("observe_map")))
    errors.extend(validate_verification_views(board.get("verification_views")))
    errors.extend(validate_power_and_boot(board.get("power_and_boot")))
    if "bench_setup" in test:
        errors.extend(validate_bench_setup(test.get("bench_setup"), source_name="bench_setup"))
    if "connections" in test:
        errors.extend(validate_bench_setup(test.get("connections"), source_name="connections"))
    return errors
