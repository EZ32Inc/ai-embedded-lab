from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class InstrumentProvider:
    family: str
    native_interface_profile: Callable[[], Dict[str, Any]]
    identify: Callable[[Dict[str, Any]], Dict[str, Any]]
    get_capabilities: Callable[[Dict[str, Any]], Dict[str, Any]]
    get_status: Callable[[Dict[str, Any]], Dict[str, Any]]
    doctor: Callable[[Dict[str, Any]], Dict[str, Any]]
    actions: Dict[str, Callable[..., Dict[str, Any]]]

    def invoke_action(self, config: Dict[str, Any], action: str, **kwargs: Any) -> Dict[str, Any]:
        handler = self.actions.get(action)
        if handler is None:
            return {
                "status": "error",
                "error": {
                    "code": "unsupported_action",
                    "message": f"unsupported action: {action}",
                    "retryable": False,
                },
            }
        return handler(config, **kwargs)
