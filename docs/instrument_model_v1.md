# Instrument Model V1

## Scope

This document defines the minimal stable contract for instrument interfaces in
AEL. It is intentionally strict and small.

The model covers:

- capability taxonomy
- action contract
- result / error / fallback envelope

During migration, legacy `status/data/error` fields may remain as compatibility
aliases. New code should read `ok`, `outcome`, `family`, `action`, `result`,
and `error`.

## Capability Taxonomy

Stable vocabulary:

- `debug.attach`
- `debug.flash`
- `debug.reset`
- `capture.digital`
- `measure.digital`
- `measure.voltage`
- `stim.digital`
- `uart.bridge`
- `uart.observe`
- `health.preflight`
- `health.status`
- `health.doctor`

Capability declaration shape:

```json
{
  "capability": "debug.flash",
  "surface": "gdb_remote",
  "operations": ["program_firmware"],
  "family": "esp32jtag"
}
```

## Action Contract

Action request envelope:

```json
{
  "contract_version": "instrument_action/v1",
  "family": "esp32jtag",
  "action": "program_firmware",
  "requested": {
    "firmware_path": "/tmp/fw.elf",
    "transport": "gdb_remote"
  }
}
```

Action response envelope:

```json
{
  "contract_version": "instrument_action/v1",
  "ok": true,
  "outcome": "success",
  "family": "esp32jtag",
  "action": "program_firmware",
  "requested": {
    "firmware_path": "/tmp/fw.elf",
    "transport": "gdb_remote"
  },
  "result": {
    "firmware_path": "/tmp/fw.elf",
    "transport": "gdb_remote"
  },
  "error": null,
  "fallback": null
}
```

Action names now expected at the interface layer:

- `program_firmware`
- `capture_signature`
- `preflight_probe`
- `measure_digital`
- `measure_voltage`
- `stim_digital`
- `open`
- `close`
- `write_uart`
- `read_uart`

## Outcome Semantics

### Success

```json
{
  "ok": true,
  "outcome": "success",
  "result": {"firmware_path": "/tmp/fw.elf"}
}
```

### Failure

```json
{
  "ok": false,
  "outcome": "failure",
  "error": {
    "code": "control_program_failed",
    "message": "usb busy",
    "retryable": false,
    "boundary": "firmware_programming",
    "details": {"firmware_path": "/tmp/fw.elf"}
  },
  "fallback": {
    "strategy": "retry_after_probe_recovery",
    "suggestion": "retry after confirming probe health"
  }
}
```

### Partial Success

Partial means the action completed but with degraded semantics.

```json
{
  "ok": true,
  "outcome": "partial",
  "result": {"samples": 4096},
  "warnings": ["edge validation skipped"]
}
```

### Unsupported

```json
{
  "ok": false,
  "outcome": "unsupported",
  "error": {
    "code": "unsupported_action",
    "message": "unsupported action: capture_signature",
    "retryable": false,
    "boundary": "interface_contract"
  },
  "fallback": {
    "strategy": "switch_instrument_family",
    "suggestion": "use an instrument that declares capture.digital"
  }
}
```

## Family Examples

### ESP32 JTAG `program_firmware`

```json
{
  "contract_version": "instrument_action/v1",
  "ok": true,
  "outcome": "success",
  "family": "esp32jtag",
  "action": "program_firmware",
  "requested": {
    "firmware_path": "/tmp/fw.elf",
    "transport": "gdb_remote"
  },
  "result": {
    "firmware_path": "/tmp/fw.elf",
    "transport": "gdb_remote",
    "managed_debug_server": null
  }
}
```

### ST-Link `program_firmware`

```json
{
  "contract_version": "instrument_action/v1",
  "ok": false,
  "outcome": "failure",
  "family": "stlink",
  "action": "program_firmware",
  "requested": {
    "firmware_path": "/tmp/fw.elf",
    "transport": "gdb_remote"
  },
  "error": {
    "code": "control_program_failed",
    "message": "usb busy",
    "retryable": false,
    "boundary": "firmware_programming"
  },
  "fallback": {
    "strategy": "retry_after_probe_recovery",
    "suggestion": "retry after confirming ST-Link probe health or restarting the managed local GDB server"
  }
}
```

### ESP32 Meter `measure_digital`

```json
{
  "contract_version": "instrument_action/v1",
  "ok": true,
  "outcome": "success",
  "family": "esp32_meter",
  "action": "measure_digital",
  "requested": {
    "pins": [11, 12],
    "duration_ms": 250
  },
  "result": {
    "pins": {
      "11": {"state": "toggle"},
      "12": {"state": "high"}
    }
  }
}
```
