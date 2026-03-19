from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class StlinkCapabilities:
    instrument_name: str = "stlink"
    supports_flash: bool = True
    supports_reset: bool = True
    supports_gpio_measure: bool = False
    supports_debug_halt: bool = True
    supports_debug_read_memory: bool = True
    transport: str = "gdb_remote"
    version: str = "v0.2"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CAPABILITIES = StlinkCapabilities()
