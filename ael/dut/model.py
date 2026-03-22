"""
DUT data model.

DUTConfig is the canonical representation of a Device Under Test.
It replaces direct dict access to board YAML configs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProcessorConfig:
    """Single processor on a DUT board."""
    id: str                          # e.g. "esp32c3", "rp2040"
    arch: str                        # e.g. "riscv", "xtensa", "arm"
    role: str = "primary"            # "primary" | "secondary"
    clock_hz: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"id": self.id, "arch": self.arch, "role": self.role}
        if self.clock_hz is not None:
            d["clock_hz"] = self.clock_hz
        d.update(self.extra)
        return d


@dataclass
class DUTConfig:
    """
    Board-first DUT configuration.

    Replaces the raw board_cfg dict throughout the codebase.
    Provides backward-compatible .mcu property and .to_legacy_dict() method
    so existing callers can be migrated incrementally.
    """
    board_id: str
    name: str
    processors: List[ProcessorConfig]
    build: Dict[str, Any] = field(default_factory=dict)
    flash: Dict[str, Any] = field(default_factory=dict)
    observe_map: Dict[str, Any] = field(default_factory=dict)
    observe: Dict[str, Any] = field(default_factory=dict)
    pins: Dict[str, Any] = field(default_factory=dict)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    instrument: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)
    # Phase 2: DUT↔Test applicability
    kind: str = "board"                    # bare_mcu | soc | board | module | fpga_target | mixed_system
    features: List[str] = field(default_factory=list)  # e.g. ["programmable_via_swd", "has_gpio"]

    # ── Backward-compat accessors ──────────────────────────────────────────

    @property
    def primary_processor(self) -> ProcessorConfig:
        """Return the primary processor, or first processor if none marked."""
        for p in self.processors:
            if p.role == "primary":
                return p
        if self.processors:
            return self.processors[0]
        raise ValueError(f"DUT {self.board_id!r} has no processors defined")

    @property
    def mcu(self) -> str:
        """
        Backward-compat: return primary processor id.
        Replaces manifest.get('mcu') and board_cfg.get('target') call sites.
        Returns empty string if no processors defined.
        """
        if not self.processors:
            return ""
        return self.primary_processor.id

    @property
    def target(self) -> str:
        """Alias of mcu for build/flash toolchain compat."""
        return self.mcu

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Serialize back to the flat board_cfg dict shape that
        strategy_resolver.py, pipeline.py, and default_verification.py
        currently expect.

        This shim lets those files remain unchanged during Step 2 migration.
        Once all callers are updated, this method can be removed.
        """
        d: Dict[str, Any] = {
            "name": self.name,
            "target": self.mcu,
        }
        if self.build:
            d["build"] = dict(self.build)
        if self.flash:
            d["flash"] = dict(self.flash)
        if self.observe_map:
            d["observe_map"] = dict(self.observe_map)
        if self.observe:
            d["observe"] = dict(self.observe)
        if self.pins:
            d["pins"] = dict(self.pins)
        if self.capabilities:
            d["capabilities"] = dict(self.capabilities)
        if self.instrument:
            d["instrument"] = dict(self.instrument)
        # Emit clock_hz from primary processor if present
        if self.processors and self.primary_processor.clock_hz is not None:
            d["clock_hz"] = self.primary_processor.clock_hz
        d.update(self.extra)
        return d
