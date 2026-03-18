from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Esp32JtagCapabilities:
    instrument_name: str = "esp32_jtag"
    supports_flash: bool = True
    supports_reset: bool = True
    supports_gpio_measure: bool = True
    supports_debug_halt: bool = False
    supports_debug_read_memory: bool = False
    transport: str = "network"
    version: str = "v0.1"

    def to_dict(self) -> dict:
        return asdict(self)


CAPABILITIES = Esp32JtagCapabilities()
