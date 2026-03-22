# Instrument Spec Migration Plan (v1)

**Status:** Draft

---

## Goal

Introduce the new instrument spec (action-based model) with:

- Minimal disruption
- Backward compatibility
- Incremental validation

---

## Strategy

Two-phase approach:

1. Validate spec using existing instruments
2. Introduce new local UART instrument

---

## Phase 1 — Validate Spec with Existing Instruments

### Objective

Ensure the new spec can describe existing instruments without breaking behavior.

---

### Steps

#### 1. Select representative instruments

Choose 1–2 existing instruments:
- One network-based (e.g. `uart_bridge` via TCP)
- One complex instrument (if available)

#### 2. Write equivalent v1 spec

Create new spec files using the new format.

> Do NOT modify existing implementation yet.

#### 3. Map actions

Translate current usage into actions.

**Before:**
```python
read_uart()
```

**After:**
```yaml
action: uart_read
backend: network_rpc
```

#### 4. Build minimal adapter

Add a thin adapter layer:

```
instrument_spec → action → existing implementation
```

No full refactor required.

#### 5. Validate

Verify:
- Same functionality works
- No regression
- Actions map cleanly

---

### Exit Criteria

- At least one existing instrument runs fully via new spec
- No schema awkwardness observed

---

## Phase 2 — Add Local UART Instrument

### Objective

Validate the native (non-network) instrument path.

---

### Steps

#### 1. Define UART instrument spec

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

#### 2. Implement backend

Create minimal backend: `pyserial_backend.py`

Support:
- `uart_read`
- `uart_write`

#### 3. Integrate with execution path

Extend instrument execution:

```python
if backend == "network_rpc":
    use existing client

elif backend == "pyserial":
    use local serial backend
```

#### 4. Run real test

Use real hardware:
- Connect UART device
- Run read / write
- Validate data

---

### Exit Criteria

- Local UART works without network wrapper
- Same action model works for both network and local

---

## Phase 3 — (Future, optional)

Not required now. Possible future work:

- More backends (`esp_idf`, `openocd`)
- Richer action schema
- Capability-based auto-selection
- Schema v2

---

## Non-Goals

- No full rewrite of existing system
- No immediate migration of all instruments
- No transport-level abstraction explosion

---

## Key Principles

| Principle | Detail |
|-----------|--------|
| Minimal change first | Validate before expanding |
| Real use case | Prove with actual hardware |
| Keep old system working | No big-bang cutover |
| Grow only when needed | Avoid premature complexity |

---

## Summary

This migration:

1. Introduces the action-based instrument model
2. Validates it against the existing system
3. Proves native instrument support (local UART)
4. Avoids premature complexity
