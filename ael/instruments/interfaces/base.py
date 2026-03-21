from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict

from ael.instruments.interfaces.model import action_unsupported

_log = logging.getLogger(__name__)

# Model-v1 envelope marker fields.  Every action handler registered in
# InstrumentProvider.actions must return a dict that contains at least
# these keys.  Handlers that bypass wrap_legacy_action / action_success /
# action_failure will trigger a warning so the gap is visible in logs.
_MODEL_V1_REQUIRED = frozenset({"ok", "outcome", "action"})


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
        result = handler(config, **kwargs)
        missing = _MODEL_V1_REQUIRED - set(result or {})
        if missing:
            _log.warning(
                "instrument provider %r action %r returned a non-model-v1 envelope "
                "(missing fields: %s); handler must go through wrap_legacy_action / "
                "action_success / action_failure",
                self.family,
                action,
                ", ".join(sorted(missing)),
            )
        return result
