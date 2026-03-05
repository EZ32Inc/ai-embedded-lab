from __future__ import annotations

import warnings
from typing import Any, Dict

from ael.instruments.manifest import load_manifests


def load_manifest(instrument_id: str) -> Dict[str, Any]:
    """
    Temporary compatibility shim.

    Canonical manifest loading now lives in ``ael.instruments.manifest``.
    """
    if not instrument_id or not str(instrument_id).strip():
        raise ValueError("instrument_id is required")
    warnings.warn(
        "ael.instrument_manifest.load_manifest() is deprecated; use "
        "ael.instruments.manifest.load_manifests() or "
        "ael.instruments.registry.InstrumentRegistry",
        DeprecationWarning,
        stacklevel=2,
    )
    manifests = load_manifests()
    data = manifests.get(str(instrument_id).strip())
    if not isinstance(data, dict):
        raise FileNotFoundError(f"instrument manifest not found for id: {instrument_id}")
    return dict(data)
