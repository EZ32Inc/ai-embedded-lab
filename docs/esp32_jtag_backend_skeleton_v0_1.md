# ESP32-JTAG Backend Skeleton v0.1

Date: 2026-03-18
Status: Active Draft

## Purpose

This document defines the recommended backend skeleton for the ESP32-JTAG reference implementation.

It is not a full implementation spec.
It is the shape that implementation should follow so the instrument can serve as the AEL reference backend.

Parent document:

- [ael_instrument_layer_v1_0.md](./ael_instrument_layer_v1_0.md)

Related execution docs:

- [esp32_jtag_action_mapping_v0_1.md](./esp32_jtag_action_mapping_v0_1.md)
- [esp32_jtag_validation_plan_v0_1.md](./esp32_jtag_validation_plan_v0_1.md)

## Design Goals

The skeleton should make these boundaries obvious:

- backend dispatch
- transport communication
- per-action logic
- error typing and normalization
- capability declaration

The skeleton should be:

- simple
- AI-readable
- reusable as the future template for other instruments

## Recommended Layout

```text
instruments/
  esp32_jtag/
    __init__.py
    backend.py
    transport.py
    errors.py
    capability.py
    actions/
      __init__.py
      flash.py
      reset.py
      gpio_measure.py
      debug_halt.py
      debug_read_memory.py
```

## File Responsibilities

### `backend.py`

Owns:

- supported action registration
- `execute(action, params)` dispatch
- normalization of exceptions into IAM failure shape
- capability exposure

Should not own:

- socket protocol details
- long per-action logic
- raw response parsing policy for every action

### `transport.py`

Owns:

- connection config
- request send/receive
- timeout handling
- framing and response decoding

Should not own:

- IAM action validation
- AEL workflow decisions
- result normalization policy

### `errors.py`

Owns:

- typed backend exceptions
- mapping from exception type to error code

### `capability.py`

Owns:

- explicit capability declaration
- version and support flags

### `actions/*.py`

Each action module owns:

- request validation
- request-to-transport payload mapping
- normalized success result construction

## Normalized Result Shapes

### Success

```json
{
  "status": "success",
  "action": "gpio_measure",
  "data": {},
  "logs": []
}
```

### Failure

```json
{
  "status": "failure",
  "action": "gpio_measure",
  "error": {
    "code": "measurement_failure",
    "message": "gpio_measure failed",
    "details": {}
  }
}
```

## Suggested Error Types

```python
class Esp32JtagError(Exception):
    pass

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
```

## Suggested Error Code Mapping

```python
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
```

## Capability Shape

Suggested initial capability declaration:

```python
{
    "instrument_name": "esp32_jtag",
    "supports_flash": True,
    "supports_reset": True,
    "supports_gpio_measure": True,
    "supports_debug_halt": False,
    "supports_debug_read_memory": False,
    "transport": "network",
    "version": "v0.1",
}
```

## Backend Execution Pattern

Recommended runtime pattern:

```python
def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}
    if action not in self._handlers:
        return self._error_result(
            action=action,
            code="unsupported_action",
            message=f"unsupported action: {action}",
            details={"supported_actions": sorted(self._handlers.keys())},
        )
    handler = self._handlers[action]
    try:
        return handler(self.transport, params)
    except Exception as exc:
        return self._normalize_exception(action, exc)
```

## Action Handler Pattern

Each action handler should follow the same three steps:

1. validate request
2. call transport
3. normalize success response

Example shape:

```python
def run_reset(transport, params):
    reset_kind = params.get("reset_kind", "hard")
    if reset_kind not in {"hard", "soft", "line"}:
        raise InvalidRequest("reset_kind must be one of: hard, soft, line")
    response = transport.request("reset", {"reset_kind": reset_kind})
    if response.get("ok") is not True:
        raise ResetFailure(response.get("message", "reset failed"))
    return {
        "status": "success",
        "action": "reset",
        "data": {
            "reset_kind": reset_kind,
            "elapsed_s": response.get("elapsed_s"),
            "method": response.get("method"),
        },
        "logs": response.get("logs", []),
    }
```

## Transport Pattern

The transport API should stay narrow.

Suggested shape:

```python
class Esp32JtagTransport:
    def request(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...
```

The transport may use TCP or another protocol, but backend consumers should not need to know those details.

## Integration Intent

This skeleton is not yet the final AEL integration layer.
It is the reference backend shape that AEL should wrap or adapt.

The intended sequence is:

1. build the ESP32-JTAG backend to this shape
2. prove the validation plan against it
3. connect it into the AEL instrument registry or dispatch layer
4. align other instruments to the same pattern

## Non-Goals

This skeleton does not require:

- all future actions to be implemented immediately
- final transport protocol lock-in
- full AI behavior orchestration in the same change

## Immediate Follow-Up

After this skeleton is accepted, the next coding steps should be:

1. implement `flash.py`
2. implement `reset.py`
3. implement `gpio_measure.py`
4. add explicit placeholder modules for `debug_halt.py` and `debug_read_memory.py`
5. run the validation plan

