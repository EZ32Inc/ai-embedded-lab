from __future__ import annotations


class Esp32JtagError(Exception):
    """Base exception for ESP32-JTAG backend errors."""


class InvalidRequest(Esp32JtagError):
    pass


class TransportUnavailable(Esp32JtagError):
    pass


class RequestTimeout(Esp32JtagError):
    pass


class DeviceBusy(Esp32JtagError):
    pass


class ProgrammingFailure(Esp32JtagError):
    pass


class MeasurementFailure(Esp32JtagError):
    pass


class ResetFailure(Esp32JtagError):
    pass


ERROR_CODE_MAP = {
    InvalidRequest: "invalid_request",
    TransportUnavailable: "transport_unavailable",
    RequestTimeout: "request_timeout",
    DeviceBusy: "device_busy",
    ProgrammingFailure: "programming_failure",
    MeasurementFailure: "measurement_failure",
    ResetFailure: "reset_failure",
    Esp32JtagError: "backend_error",
}


def error_code_for(exc: Exception) -> str:
    for exc_type, code in ERROR_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return "backend_error"
