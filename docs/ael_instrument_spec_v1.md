# AEL Instrument Spec (v1)

**Schema Version:** 1
**Status:** Draft

---

## Overview

This spec defines how instruments are described in AEL.

**Goals:**
- Describe what an instrument is
- Describe what actions it supports
- Describe how those actions are executed

**Non-goals:**
- Do not over-model transport (USB / serial / network)
- Do not enforce a single access method

---

## Schema Version

Each instrument must declare:

```yaml
schema_version: 1
```

This allows future evolution without breaking existing definitions.

---

## Core Structure

```yaml
schema_version: 1

instrument:
  id: <string>
  kind: <string>

  capabilities: [<string>, ...]

  actions:
    - name: <string>
      backend: <string>
      params: [<string>, ...]
```

---

## Fields

### `id`

Unique identifier of the instrument.

```
esp32_dev
uart0
remote_uart_1
```

---

### `kind`

Type / category of the instrument.

```
uart_bridge
esp32_dev_interface
jtag_probe
meter
```

---

### `capabilities`

High-level abilities of the instrument.

```
uart_txrx
flash
monitor
reset
measure_voltage
```

Used for:
- Program compatibility checking
- Capability reasoning

---

### `actions`

Defines what operations the instrument supports.

Each action includes:

| Field | Description | Examples |
|-------|-------------|---------|
| `name` | Logical operation name | `uart_read`, `flash`, `reset` |
| `backend` | How this action is executed | `network_rpc`, `esp_idf`, `pyserial`, `openocd` |
| `params` | Required parameters | `port`, `baudrate`, `timeout`, `project_dir` |

---

## Design Principles

### 1. Action-first model

Instruments are defined by what they can **do** (actions), not how they are accessed.

### 2. Transport-agnostic

Do **not** model USB / serial / network at the schema top level.
These belong to backend implementation.

### 3. Minimal completeness

Spec should be just enough to:
- Select instrument
- Execute action
- Pass parameters

### 4. Backend responsibility

Backend handles:
- Transport (serial / network / USB)
- Tool invocation
- Protocol details

---

## Examples

### Example 1: ESP32 (local tool)

```yaml
schema_version: 1

instrument:
  id: esp32_dev
  kind: esp32_dev_interface

  capabilities: [flash, monitor, reset]

  actions:
    - name: flash
      backend: esp_idf
      params: [port, project_dir]

    - name: monitor
      backend: esp_idf
      params: [port]
```

---

### Example 2: UART (local serial)

```yaml
schema_version: 1

instrument:
  id: uart0
  kind: uart_bridge

  capabilities: [uart_txrx]

  actions:
    - name: uart_read
      backend: pyserial
      params: [port, baudrate, timeout]

    - name: uart_write
      backend: pyserial
      params: [port, baudrate, data]
```

---

### Example 3: UART (network)

```yaml
schema_version: 1

instrument:
  id: remote_uart
  kind: uart_bridge

  capabilities: [uart_txrx]

  actions:
    - name: uart_read
      backend: network_rpc
      params: [endpoint, timeout]

    - name: uart_write
      backend: network_rpc
      params: [endpoint, data]
```

---

## Summary

An instrument in AEL is:

> A capability provider defined by its actions, with execution delegated to a backend.
