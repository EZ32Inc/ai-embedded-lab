"""
Action Registry for Instrument Action Model v0.1.

Defines the canonical set of supported actions, their required/optional request
fields, and representative error codes.
"""

ACTION_REGISTRY = {
    "flash": {
        "required_request_fields": ["firmware"],
        "optional_request_fields": ["format", "erase", "verify", "reset_after"],
        "description": "Program firmware to a DUT.",
    },
    "reset": {
        "required_request_fields": [],
        "optional_request_fields": ["mode"],
        "description": "Reset the DUT to a known state.",
    },
    "uart_read": {
        "required_request_fields": [],
        "optional_request_fields": ["baud", "duration_s"],
        "description": "Read UART output for a defined period.",
    },
    "uart_wait_for": {
        "required_request_fields": ["pattern"],
        "optional_request_fields": ["baud", "timeout_s"],
        "description": "Wait until UART output contains a given pattern or timeout.",
    },
    "gpio_measure": {
        "required_request_fields": ["channel"],
        "optional_request_fields": ["mode", "duration_s"],
        "description": "Measure a GPIO or digital signal channel.",
    },
    "voltage_read": {
        "required_request_fields": ["channel"],
        "optional_request_fields": [],
        "description": "Read a voltage channel associated with a DUT or instrument.",
    },
    "stim_digital": {
        "required_request_fields": ["gpio", "mode"],
        "optional_request_fields": ["duration_us", "freq_hz", "pattern", "keep"],
        "description": "Drive a digital stimulus on an instrument-controlled GPIO.",
    },
    "debug_halt": {
        "required_request_fields": [],
        "optional_request_fields": [],
        "description": "Halt the DUT CPU through a debug-capable instrument.",
    },
    "debug_read_memory": {
        "required_request_fields": ["address", "length"],
        "optional_request_fields": [],
        "description": "Read memory through a debug-capable instrument.",
    },
}

KNOWN_ERROR_CODES = [
    "connection_timeout",
    "not_supported",
    "invalid_request",
    "program_failed",
    "verify_failed",
    "pattern_not_found",
    "measurement_failed",
    "target_not_halted",
    "no_instrument_available",
    "unknown_action",
    "missing_required_field",
]


def validate_action(action: str, request: dict) -> str | None:
    """Validate action name and required request fields.

    Returns an error message string if validation fails, or None if OK.
    """
    if action not in ACTION_REGISTRY:
        return f"Unknown action '{action}'. Known actions: {sorted(ACTION_REGISTRY)}"
    spec = ACTION_REGISTRY[action]
    for field in spec["required_request_fields"]:
        if field not in request:
            return f"Action '{action}' requires request field '{field}'"
    return None


def list_actions() -> list[str]:
    return sorted(ACTION_REGISTRY)
