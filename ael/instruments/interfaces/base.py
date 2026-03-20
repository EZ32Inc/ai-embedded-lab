from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from ael.instruments.interfaces.model import action_unsupported


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
            return action_unsupported(
                family=self.family,
                action=action,
                supported_actions=sorted(self.actions),
            )
        return handler(config, **kwargs)
