from __future__ import annotations


CAPABILITIES = {
    "uart_read": {
        "request": {
            "required": [],
            "optional": ["baud", "duration_s"],
        }
    },
    "uart_wait_for": {
        "request": {
            "required": ["pattern"],
            "optional": ["baud", "timeout_s"],
        }
    },
}
