"""
Instrument Spec Loader — Schema Version 1.

Loads instrument spec YAML files (schema_version: 1) and exposes
a minimal InstrumentSpec dataclass for use by spec_executor.

YAML format:

    schema_version: 1

    instrument:
      id: uart0
      kind: uart_bridge
      capabilities: [uart_txrx]
      actions:
        - name: uart_read
          backend: pyserial
          params: [port, baudrate, timeout]

Usage:

    from ael.instruments.spec_loader import load_spec, load_specs_dir

    spec = load_spec("configs/instrument_specs/uart0_local.yaml")
    spec.get_action("uart_read")  # -> ActionSpec(name=..., backend=..., params=...)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ActionSpec:
    name: str
    backend: str  # "network_rpc" | "pyserial" | "esp_idf" | "openocd"
    params: list[str] = field(default_factory=list)


@dataclass
class InstrumentSpec:
    id: str
    kind: str
    capabilities: list[str] = field(default_factory=list)
    actions: list[ActionSpec] = field(default_factory=list)

    def get_action(self, name: str) -> ActionSpec | None:
        for a in self.actions:
            if a.name == name:
                return a
        return None

    def supports(self, action_name: str) -> bool:
        return self.get_action(action_name) is not None


def _parse(data: dict[str, Any]) -> InstrumentSpec:
    version = data.get("schema_version")
    if version != 1:
        raise ValueError(f"Unsupported schema_version: {version!r} (expected 1)")
    inst = data.get("instrument") or {}
    actions = [
        ActionSpec(
            name=str(a.get("name") or ""),
            backend=str(a.get("backend") or ""),
            params=list(a.get("params") or []),
        )
        for a in (inst.get("actions") or [])
        if a.get("name")
    ]
    return InstrumentSpec(
        id=str(inst.get("id") or ""),
        kind=str(inst.get("kind") or ""),
        capabilities=list(inst.get("capabilities") or []),
        actions=actions,
    )


def load_spec(path: str | Path) -> InstrumentSpec:
    """Load a single v1 instrument spec from a YAML file."""
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return _parse(data)


def load_specs_dir(directory: str | Path) -> dict[str, InstrumentSpec]:
    """Load all v1 instrument specs from a directory.

    Returns a dict keyed by instrument id.
    """
    directory = Path(directory)
    specs: dict[str, InstrumentSpec] = {}
    for p in sorted(directory.glob("*.yaml")):
        try:
            spec = load_spec(p)
            if spec.id:
                specs[spec.id] = spec
        except Exception as exc:
            print(f"spec_loader: skipping {p.name}: {exc}")
    return specs
