"""
Instrument selection logic for Instrument Action Model v0.1.

v0.1 strategy:
- if one instrument supports the action, use it
- if multiple instruments support the action, use the first in attached_instruments order
- if none match, return None
"""

from __future__ import annotations

from .config_loader import InstrumentCatalog


def select_instrument_for_action(
    dut_name: str,
    action: str,
    catalog: InstrumentCatalog,
) -> dict | None:
    """Return the first attached instrument that supports *action*, or None."""
    instruments = catalog.get_attached_instruments(dut_name)
    for inst in instruments:
        supported = inst.get("supports") or []
        if action in supported:
            return inst
    return None
