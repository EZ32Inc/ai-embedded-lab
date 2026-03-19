from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ael.adapters import esp32s3_dev_c_meter_tcp

from .errors import InvalidRequest, MeasurementFailure, StimulusFailure, TransportUnavailable


@dataclass(frozen=True)
class TransportConfig:
    host: str
    port: int
    timeout_s: float = 3.0


class Esp32MeterTransport:
    def __init__(self, cfg: TransportConfig) -> None:
        self.cfg = cfg

    def _adapter_cfg(self) -> dict[str, Any]:
        return {
            "host": self.cfg.host,
            "port": self.cfg.port,
            "timeout_s": self.cfg.timeout_s,
        }

    def request(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            if command == "gpio_measure":
                pins = payload.get("channels") or []
                if not isinstance(pins, list) or not pins:
                    raise InvalidRequest("gpio_measure requires non-empty 'channels' list")
                duration_ms = int(payload.get("duration_ms") or 500)
                return esp32s3_dev_c_meter_tcp.measure_digital(
                    self._adapter_cfg(),
                    pins=[int(p) for p in pins],
                    duration_ms=duration_ms,
                )
            if command == "voltage_read":
                gpio = payload.get("gpio")
                if gpio is None:
                    raise InvalidRequest("voltage_read requires 'gpio'")
                avg = int(payload.get("avg") or 16)
                return esp32s3_dev_c_meter_tcp.measure_voltage(
                    self._adapter_cfg(),
                    gpio=int(gpio),
                    avg=avg,
                )
            if command == "stim_digital":
                gpio = payload.get("gpio")
                mode = payload.get("mode")
                if gpio is None or not str(mode or "").strip():
                    raise InvalidRequest("stim_digital requires 'gpio' and 'mode'")
                return esp32s3_dev_c_meter_tcp.stim_digital(
                    self._adapter_cfg(),
                    gpio=int(gpio),
                    mode=str(mode),
                    duration_us=payload.get("duration_us"),
                    freq_hz=payload.get("freq_hz"),
                    pattern=payload.get("pattern"),
                    keep=int(payload.get("keep") or 0),
                )
        except (InvalidRequest, MeasurementFailure, StimulusFailure):
            raise
        except Exception as exc:
            raise TransportUnavailable(str(exc)) from exc
        raise InvalidRequest(f"unsupported meter command: {command}")

    @staticmethod
    def ensure_ok(response: dict[str, Any], *, action: str) -> dict[str, Any]:
        if not isinstance(response, dict):
            raise MeasurementFailure(f"{action} returned invalid response")
        if response.get("type") == "error":
            message = str(response.get("message") or response)
            if action == "stim_digital":
                raise StimulusFailure(message)
            raise MeasurementFailure(message)
        return response

