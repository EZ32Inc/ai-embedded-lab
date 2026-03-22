# Onboard Instrument Support — Implementation Plan v0.1

**Date:** 2026-03-22
**Status:** Draft — awaiting review
**Relates to:** `ael_board_dut_definition_spec_v0_1.md`, `ael_auto_test_generation_experiment_spec_v0_1.md`

---

## 1. Problem Statement

### 1.1 Current Assumption (Being Changed)

The entire current AEL codebase assumes:

> **board = DUT**

This assumption is embedded in:
- Board YAML files (board config IS the DUT config)
- Test plan specs (`"board": "stm32f411ceu6"` means both the board and the DUT)
- `strategy_resolver.py` — reads instrument from test spec, no board-level instrument concept
- `civilization/run_index.py` — uses `board_id` as DUT identifier
- `pipeline.py` — loads board YAML and treats it directly as DUT config

### 1.2 New Reality

A board is a physical assembly.
It may contain one or more DUTs **and** one or more instruments.

**Concrete scenario driving this change:**

```
Board: ESP32S3 Custom Board
  ├── DUT: ESP32S3 MCU (the thing being tested)
  ├── Instrument A: USB-UART bridge type X (e.g. CP2102)
  └── Instrument B: USB-UART bridge type Y (e.g. CH343)

Rules:
  - Only one bridge is connected to the PC at a time
  - Both bridges connect to the same UART1 on the ESP32S3
  - The connected bridge is used for BOTH flash and UART observation
  - Both bridges run the same firmware (same binary)
  - The two bridge types are different (different USB VID/PID)
```

This differs from existing boards in a fundamental way:

| Aspect | Existing boards | New scenario |
|--------|----------------|--------------|
| Flash path | External ESP32JTAG (SWD) | Onboard USB-UART bridge (esptool via serial) |
| Observe path | External logic capture | Same bridge, same serial port |
| Instrument source | Hardcoded in test spec | Declared on board, selected at runtime |
| Board = DUT | Implicit | Explicitly separated |

### 1.3 Other Boards to Consider

- Some boards may have **multiple DUTs** (not this ESP32S3 case, but planned for others)
- Some boards may have **same-type bridges** across different boards
- The architecture must support all these without breaking existing boards

---

## 2. Design Principles

1. **Backward compatibility is mandatory.** All existing boards and test plans work unchanged.
2. **Additive, not replacement.** New fields are optional; absence means old behavior.
3. **Board declares, test requests, runtime selects.** The board knows what it has; the test says what it needs; AEL picks at runtime.
4. **`dut_id` defaults to `board_id`.** Existing code that uses `board_id` as DUT identity remains correct for single-DUT boards.
5. **One instrument per test run.** The two-bridge scenario is "either/or", not simultaneous. Selection happens before the run starts.

---

## 3. Data Model Changes

### 3.1 Board YAML Schema Extension

**Current (unchanged for existing boards):**
```yaml
board:
  name: STM32F411 Black Pill
  target: stm32f411ceu6
  processors:
    - id: stm32f411ceu6
      arch: cortex-m4
      role: primary
  build:
    type: cmake_arm
  flash:
    method: openocd_swd
```

**New (for boards with onboard instruments):**
```yaml
board:
  id: esp32s3_custom
  name: ESP32S3 Custom Board

dut:
  id: esp32s3
  type: esp32s3
  arch: xtensa
  flash:
    method: esptool_uart      # flash via serial (not SWD)

instruments:
  - id: bridge_a
    type: usb_uart_bridge
    location: onboard
    targets: [esp32s3]        # which DUT(s) this instrument serves
    detect:
      usb_vid: "10C4"         # CP2102
      usb_pid: "EA60"
    capabilities:
      - uart_observe
      - esptool_flash

  - id: bridge_b
    type: usb_uart_bridge
    location: onboard
    targets: [esp32s3]
    detect:
      usb_vid: "1A86"         # CH343
      usb_pid: "55D3"
    capabilities:
      - uart_observe
      - esptool_flash
```

**Rules:**
- If `instruments:` is absent → board is treated as single DUT, existing behavior
- If `dut:` is absent → `dut.id = board.id` (backward compat)
- `targets:` links instruments to DUTs on the same board
- `detect.usb_vid/pid` is used by the instrument detector at runtime

### 3.2 Test Plan Schema Extension

**Current (still supported, unchanged):**
```json
{
  "name": "esp32c6_uart_banner",
  "board": "esp32c6_devkit",
  "instrument": {
    "id": "esp32s3_dev_c_meter"
  }
}
```

**New (for onboard-instrument boards):**
```json
{
  "name": "esp32s3_uart_smoke",
  "board": "esp32s3_custom",
  "dut_id": "esp32s3",
  "supported_instruments": ["usb_uart_bridge"],
  "observe_uart": {
    "port": "__instrument_port__",
    "baud": 115200,
    "expect_patterns": ["AEL_READY ESP32S3"]
  },
  "build": {
    "project_dir": "firmware/targets/esp32s3_uart_smoke",
    "build_dir": "artifacts/build_esp32s3_uart_smoke"
  }
}
```

**New fields:**

| Field | Type | Meaning |
|-------|------|---------|
| `dut_id` | string (optional) | Which DUT on the board. Defaults to `board` value if absent. |
| `supported_instruments` | list (already exists) | Instrument types acceptable. Now actually used for selection. |
| `__instrument_port__` | magic string | Replaced at runtime with the selected instrument's resolved port. |

**Selection logic (priority):**
1. If `instrument.id` is set → use it directly (existing behavior, fully backward compat)
2. If `supported_instruments` is set and board has `instruments:` → select via runtime detection
3. Otherwise → existing fallback behavior

---

## 4. New Component: `instrument_detector.py`

**Location:** `ael/instrument_detector.py`

**Purpose:** At runtime, determine which onboard instruments are currently connected to the PC and what port they appear on.

**Interface:**
```python
def detect_onboard_instruments(
    board_instruments: List[dict],
) -> List[DetectedInstrument]:
    """
    Given a list of instrument definitions from board YAML,
    return those currently present on the system with their resolved ports.

    Each DetectedInstrument contains:
      id:    instrument id from board YAML
      type:  instrument type (e.g. "usb_uart_bridge")
      port:  actual /dev/ttyUSB* or /dev/ttyACM* path
      score: preference score (onboard = high)
    """
```

**Detection mechanism:**
- Enumerate `/dev/ttyUSB*` and `/dev/ttyACM*`
- For each device, read USB VID/PID from `/sys/bus/usb-serial/` or via `pyserial`
- Match against `detect.usb_vid` / `detect.usb_pid` from board YAML
- Return matched instruments with resolved ports

**Fallback (when VID/PID not declared):**
- If `detect` is absent but instrument type is known → use heuristic (e.g., first available ttyUSB)
- Log which instrument was selected and why

---

## 5. Changes to `strategy_resolver.py`

### 5.1 Current flow (preserved for existing tests)

```
test_raw.instrument.id → load from registry → return (id, tcp_cfg, manifest)
```

### 5.2 New flow (when board has `instruments:`)

```
If test_raw has instrument.id:
  → existing flow (unchanged)

Else if board_cfg has instruments: AND test_raw has supported_instruments:
  → call instrument_detector.detect_onboard_instruments(board_instruments)
  → filter by supported_instruments types
  → select first available match
  → resolve port
  → return selected instrument

Else:
  → existing fallback (unchanged)
```

### 5.3 Port substitution

After instrument selection, scan `observe_uart.port` and `bench_setup` for `__instrument_port__` and replace with the resolved port.

### 5.4 Flash port routing

When `dut.flash.method = esptool_uart`:
- Use selected instrument's port as the esptool `-p` argument
- This replaces the current SWD-based flash path for this board type

---

## 6. Changes to `pipeline.py`

**Minimal changes:**

1. When loading board YAML, check for `instruments:` key — if present, pass to strategy_resolver
2. When building the run strategy, accept the selected instrument's port for flash (new `esptool_uart` method)
3. Pass `dut_id` through the run context (defaults to `board_id` if absent)

**No structural changes to the pipeline stages.** The existing preflight → build → flash → run → check sequence is unchanged. Only the instrument binding at the start of the run changes.

---

## 7. Changes to `civilization/run_index.py`

**Current key:** `(board_id, test_name)`
**New key:** `(dut_id, test_name)` where `dut_id = board_id` if not specified

This is a **one-line change** in `make_signature()`:

```python
def make_signature(board_id: str, test_name: str, dut_id: str = "") -> str:
    effective_id = dut_id if dut_id else board_id
    return f"{effective_id}|{test_name}"
```

All existing callers pass no `dut_id` → behavior unchanged.

---

## 8. Backward Compatibility Summary

| Existing thing | Impact |
|---------------|--------|
| All existing board YAMLs | Zero change. No `instruments:` key → existing path. |
| All existing test plans | Zero change. `instrument.id` present → existing path. |
| `civilization/run_index.py` | Zero change. `dut_id` absent → `board_id` used as before. |
| `pipeline.py` stages | Zero change. Same preflight/build/flash/run/check sequence. |
| Default verification | Zero change. All 6 existing programs unaffected. |

---

## 9. New Files and Changed Files

### New files
| File | Purpose |
|------|---------|
| `ael/instrument_detector.py` | Runtime USB VID/PID detection → port resolution |
| `configs/boards/esp32s3_custom.yaml` | First board using new schema |
| `tests/plans/esp32s3_uart_smoke.json` | First test using new instrument selection |

### Changed files
| File | Change |
|------|--------|
| `ael/strategy_resolver.py` | Add instrument selection branch (~50 lines) |
| `ael/pipeline.py` | Load board instruments; route `esptool_uart` flash |
| `ael/civilization/run_index.py` | `make_signature()` accepts optional `dut_id` |
| `ael/test_plan_schema.py` | Add `dut_id`, `__instrument_port__` to schema |

### Unchanged files
Everything else. Especially all existing board configs and test plans.

---

## 10. Implementation Order

1. **`instrument_detector.py`** — standalone, testable in isolation
2. **Board YAML schema** — `esp32s3_custom.yaml` as first example
3. **`strategy_resolver.py`** — instrument selection branch
4. **`pipeline.py`** — `esptool_uart` flash method + instrument port routing
5. **`civilization/run_index.py`** — `dut_id` parameter
6. **First test plan** — `esp32s3_uart_smoke.json`
7. **Smoke run** — verify end-to-end with the new board

---

## 11. What This Does NOT Change

- The concept of external instruments (ESP32JTAG, ST-Link, ESP32 meter) — unchanged
- How existing boards are configured — unchanged
- The three-layer experience system (Civilization Engine) — unchanged except `dut_id` defaulting
- The pack system — unchanged
- Default verification — unchanged

---

## 12. Open Questions (For Review)

1. **Multi-DUT boards**: This plan supports `dut:` as singular. When multiple DUTs are needed, `dut:` becomes `duts:` (list). Not implemented in this version — deferred.

2. **Instrument priority**: When two bridges are both connected simultaneously (unlikely but possible), which one wins? Current proposal: first match by detection order. Should this be configurable?

3. **esptool_uart flash method**: Does the existing ESP32 build/flash infrastructure already support specifying the port, or does that need a new code path? Needs verification against current `pipeline.py` ESP32 flash logic.

4. **VID/PID detection reliability**: On some Linux systems, USB serial VID/PID is available in sysfs; on others it requires `udev` rules. The detector needs to handle both. Fallback to heuristic (first available ttyUSB) needed.

5. **Same-type bridges on different boards**: If two boards each have a CP2102, both plugged in → two `/dev/ttyUSB*` devices. Detection by VID/PID alone cannot distinguish them. Future: use USB serial number or port path in sysfs. For now: user responsibility to have only one board connected at a time.
