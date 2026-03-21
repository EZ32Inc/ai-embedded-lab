from __future__ import annotations


class Esp32MeterError(Exception):
    """Base exception for ESP32 meter backend errors."""


class InvalidRequest(Esp32MeterError):
    pass


class TransportUnavailable(Esp32MeterError):
    pass


class MeasurementFailure(Esp32MeterError):
    pass


class StimulusFailure(Esp32MeterError):
    pass


ERROR_CODE_MAP = {
    InvalidRequest: "invalid_request",
    TransportUnavailable: "connection_timeout",
    MeasurementFailure: "measurement_failed",
    StimulusFailure: "stimulus_failed",
    Esp32MeterError: "backend_error",
}


def error_code_for(exc: Exception) -> str:
    for exc_type, code in ERROR_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return "backend_error"

