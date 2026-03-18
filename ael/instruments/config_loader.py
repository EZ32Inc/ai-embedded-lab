"""
Config loader for Instrument Action Model v0.1.

Loads DUT and instrument definitions from YAML files and exposes a simple
catalog interface for dispatching.

YAML format expected for a DUT:

    name: stm32f103_target_1
    role: dut
    attached_instruments:
      - stlink_1
      - usb_uart_1

YAML format expected for an instrument:

    name: esp_jtag_1
    role: instrument
    driver: esp_remote_jtag
    connection:
      host: 192.168.1.50
      port: 5555
    supports:
      - flash
      - reset
      - gpio_measure
    attached_to:
      - stm32f103_target_1

Config files may live in any directory.  Pass a list of paths to
InstrumentCatalog, or use load_catalog() which looks in the default
configs/action_model/ directory relative to the repo root.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class InstrumentCatalog:
    """In-memory catalog of DUT and instrument definitions."""

    def __init__(self, entries: list[dict[str, Any]] | None = None):
        self._duts: dict[str, dict] = {}
        self._instruments: dict[str, dict] = {}
        for entry in entries or []:
            self._register(entry)

    def _register(self, entry: dict) -> None:
        role = str(entry.get("role") or "").strip()
        name = str(entry.get("name") or "").strip()
        if not name:
            return
        if role == "dut":
            self._duts[name] = entry
        elif role == "instrument":
            self._instruments[name] = entry

    def get_dut(self, name: str) -> dict | None:
        return self._duts.get(name)

    def get_instrument(self, name: str) -> dict | None:
        return self._instruments.get(name)

    def get_attached_instruments(self, dut_name: str) -> list[dict]:
        dut = self._duts.get(dut_name)
        if not dut:
            return []
        names = dut.get("attached_instruments") or []
        result = []
        for n in names:
            inst = self._instruments.get(str(n))
            if inst:
                result.append(inst)
        return result

    def list_duts(self) -> list[str]:
        return sorted(self._duts)

    def list_instruments(self) -> list[str]:
        return sorted(self._instruments)


def _load_yaml(path: str | Path) -> dict | list | None:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_catalog_from_files(paths: list[str | Path]) -> InstrumentCatalog:
    """Load a catalog from an explicit list of YAML file paths."""
    entries: list[dict] = []
    for p in paths:
        try:
            data = _load_yaml(p)
        except Exception as exc:
            print(f"config_loader: skipping {p}: {exc}")
            continue
        if isinstance(data, list):
            entries.extend([e for e in data if isinstance(e, dict)])
        elif isinstance(data, dict):
            # Support both a bare entry dict and a top-level {"devices": [...]}
            if "devices" in data and isinstance(data["devices"], list):
                entries.extend([e for e in data["devices"] if isinstance(e, dict)])
            elif "name" in data and "role" in data:
                entries.append(data)
    return InstrumentCatalog(entries)


def load_catalog(config_dir: str | Path | None = None) -> InstrumentCatalog:
    """Load catalog from configs/action_model/ directory.

    Falls back gracefully to an empty catalog if the directory does not exist.
    """
    if config_dir is None:
        # Try to find the repo root relative to this file.
        config_dir = Path(__file__).resolve().parent.parent.parent / "configs" / "action_model"

    config_dir = Path(config_dir)
    if not config_dir.exists():
        return InstrumentCatalog()

    yaml_files = sorted(config_dir.rglob("*.yaml")) + sorted(config_dir.rglob("*.yml"))
    return load_catalog_from_files(yaml_files)
