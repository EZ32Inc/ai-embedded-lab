from __future__ import annotations


class StlinkError(Exception):
    """Base exception for ST-Link backend errors."""


class InvalidRequest(StlinkError):
    pass


class ConnectionTimeout(StlinkError):
    pass


class ProgramFailed(StlinkError):
    pass


class TargetNotHalted(StlinkError):
    pass


class MemoryReadFailed(StlinkError):
    pass


ERROR_CODE_MAP = {
    InvalidRequest: "invalid_request",
    ConnectionTimeout: "connection_timeout",
    ProgramFailed: "program_failed",
    TargetNotHalted: "target_not_halted",
    MemoryReadFailed: "verify_failed",
    StlinkError: "backend_error",
}


def error_code_for(exc: Exception) -> str:
    for exc_type, code in ERROR_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return "backend_error"
