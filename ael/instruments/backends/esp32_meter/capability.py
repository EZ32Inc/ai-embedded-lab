from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Esp32MeterCapabilities:
    instrument_name: str = "esp32_meter"
    supports_flash: bool = False
    supports_reset: bool = False
    supports_gpio_measure: bool = True
    supports_voltage_read: bool = True
    supports_stim_digital: bool = True
    transport: str = "tcp"
    version: str = "v0.1"

    def to_dict(self) -> dict:
        return asdict(self)


CAPABILITIES = Esp32MeterCapabilities()

