from __future__ import annotations

"""Compatibility shim for the old provider_registry module.

New code should prefer `ael.instruments.interfaces.registry`.
"""

from ael.instruments.interfaces.base import InstrumentProvider
from ael.instruments.interfaces.registry import resolve_control_provider, resolve_manifest_provider

__all__ = [
    "InstrumentProvider",
    "resolve_control_provider",
    "resolve_manifest_provider",
]
