# AEL Compatibility / Mapping Spec v0.1

**Status:** Draft
**Date:** 2026-03-21
**Source:** Extracted from design discussion with ChatGPT

---

## 1. Goal

Make implicit compatibility relationships between DUT, Test, and Instrument **explicit**.

After this spec is implemented, AEL should be able to:

- Know which tests can run on a given DUT
- Know which instruments are required for a given test
- Know which DUT / test combinations are feasible given the available instruments
- Provide clear reasons when a combination is not compatible
- Support automated test planning, doctor output, and future recommendation

---

## 2. The Core Problem

The current problem is not simply "missing a mapping table." What is missing is a **unified compatibility judgment model**.

Real-world compatibility is not binary yes/no:

| Example | Compatibility |
|---------|--------------|
| DUT needs 3.3V UART, instrument supports it | Compatible |
| DUT needs SWD, instrument only supports JTAG | Not compatible |
| Test needs ADC + voltage source, instrument only has ADC | Partial / insufficient |
| Board has two MCUs, test only applies to primary MCU | Conditionally compatible |
| Instrument theoretically supports it but firmware version is too old | Not currently compatible |
| Test can be done manually or automatically | Has fallback path |

Therefore this should be **capability-based compatibility resolution**, not a hard-coded pairing table.

---

## 3. Three-Layer Structure

### Layer 1 — Standard Object Definitions

Three core objects, each must explicitly declare:

- **Capability / requirements** — what it needs or provides
- **Constraints** — limitations
- **Applicability** — what it applies to
- **Optional fallbacks / alternatives**

Objects: `DUTSpec`, `TestSpec`, `InstrumentSpec`

### Layer 2 — Compatibility Engine

A unified resolver answering:

```
is_dut_test_compatible(dut, test) → CompatibilityResult
is_test_instrument_compatible(test, instrument) → CompatibilityResult
is_dut_instrument_compatible(dut, instrument) → CompatibilityResult
resolve_execution_plan(dut, test, instruments) → ExecutionPlan
```

The last function is most important — it does not just return yes/no but outputs:
- Executable or not
- Which instruments to use
- Which capabilities are missing
- Whether a fallback exists
- Why incompatible

### Layer 3 — Explicit Mapping Registry

Cache / solidify common results as an explicit registry for:
- UI display
- Doctor output
- Recommended paths
- Documentation and spec clarity

> **Principle:** Bottom layer uses capability rules as the primary source of truth. Upper layer can generate or maintain explicit mapping views.

---

## 4. The Three Mappings

### 4.1 DUT ↔ Instrument

**Question:** Can a given instrument physically/electrically/protocol-wise interface with a given DUT?

Dimensions to check:

**Interface Protocol**
- SWD, JTAG, UART, SPI, I2C, GPIO, ADC input, DAC output, PWM capture, logic analyzer channels

**Electrical Compatibility**
- IO voltage level: 1.8V / 3.3V / 5V
- Input-only / bidirectional
- Open-drain requirement
- Current drive / load limit
- Analog range
- Protection requirements

**Topology / Connection Resources**
- DUT needs 1 UART + 4 GPIO, instrument only has 2 GPIO
- DUT needs 8 LA channels, instrument only has 4

**Special Constraints**
- Instrument only supports single target
- DUT is a multi-MCU board
- Interface occupies a boot strap pin
- Instrument needs external power reference
- DUT needs isolated measurement

**Result output:**
```python
CompatibilityResult(
    compatible=True/False,
    score=0..100,
    reasons=[...],
    missing_capabilities=[...],
    warnings=[...],
    connection_requirements=[...],
)
```

---

### 4.2 DUT ↔ Test

**Question:** Does a given test apply to this DUT?

This is the most easily overlooked but most important mapping.

Test preconditions may include:
- Only for MCU, not pure FPGA
- Only for DUTs with ADC
- Only for single-board, not bare MCU
- Only for systems that have booted
- Only for DUTs with specific pinout / firmware interface / programming method

**Dimensions to check:**

DUT kind: `bare_mcu`, `soc`, `board`, `module`, `fpga_target`, `mixed_system`

DUT features:
- `has_adc`, `has_uart_console`, `has_boot_mode_control`
- `programmable_via_swd`, `programmable_via_jtag`
- `has_led`, `has_reset_pin`, `has_power_monitor_point`

**Declarative test spec example:**
```yaml
test_id: spi_loopback
applies_to:
  dut_kinds: [board, bare_mcu]
requires:
  features:
    - spi_master
    - spi_slave_or_loopback_path
optional:
  features:
    - logic_analyzer_header
excludes:
  tags:
    - no_external_io_access
```

> **Recommendation:** DUT ↔ Test compatibility should use declarative conditions, not Python code scattered across the codebase.

---

### 4.3 Test ↔ Instrument

**Question:** Does a given instrument satisfy the capability requirements of a given test at runtime?

**Key principle:** Do not write "test X can only use instrument Y." Instead write:
- What capabilities does the test require
- What capabilities does the instrument provide
- Let the resolver match them

**Test requirement example:**
```yaml
test_id: uart_echo
required_capabilities:
  - type: uart
    count: 1
    params:
      baud_min: 115200
optional_capabilities:
  - type: voltage_measure
```

**Instrument capability example:**
```yaml
instrument_id: usb_uart_bridge
provides:
  - type: uart
    count: 1
    voltage_levels: [3.3, 5.0]
```

**Multi-instrument plans:** Many tests are not completed by a single instrument but by a combination. The `resolve_execution_plan()` function must support both single-instrument and multi-instrument plans.

---

## 5. Capability Model

### Standard Capability Types

**Digital interfaces:**
`swd`, `jtag`, `uart`, `spi_master`, `spi_slave`, `i2c_master`, `gpio_input`, `gpio_output`, `logic_capture`

**Analog measurement:**
`voltage_measure`, `current_measure`, `analog_in`, `waveform_capture`

**Control:**
`power_control`, `reset_control`, `boot_mode_control`, `relay_switch`

**Programming / debug:**
`flash_program`, `debug_attach`, `trace_capture`

**System support:**
`firmware_deploy`, `serial_console`, `result_artifact_upload`

### Capabilities Are Parameterized

```python
Capability(
    type="logic_capture",
    params={
        "channels": 8,
        "max_sample_rate_hz": 100_000_000,
        "threshold_levels": [1.8, 3.3],
    }
)
```

---

## 6. Data Models

### Recommended Module Structure

```
ael/compatibility/
    __init__.py
    model.py       # Capability, Requirement, Constraint, CompatibilityResult, ExecutionPlan
    rules.py       # check_voltage_compat(), check_channel_count(), check_protocol_match()
    resolver.py    # resolve_dut_test(), resolve_test_instrument(), resolve_execution_plan()
    result.py      # Result formatting and scoring
    registry.py    # Standard capability types, test specs, instrument capabilities, rules
    explain.py     # Human-readable explanations for doctor / UI
```

### Object Spec Examples

**InstrumentSpec:**
```python
InstrumentSpec(
    instrument_type="usb_uart_bridge",
    provides=[
        Capability("uart", {"count": 1, "voltage_levels": [3.3, 5.0]}),
    ],
    controls=[],
    constraints=[],
)
```

**DUTSpec:**
```python
DUTSpec(
    dut_kind="board",
    tags=["stm32", "single_mcu"],
    features=[
        "uart_console",
        "reset_controlled",
        "boot_mode_selectable",
        "programmable_via_swd",
    ],
    interfaces=[
        Capability("uart", {"count": 1, "voltage_level": 3.3}),
        Capability("swd", {"count": 1, "voltage_level": 3.3}),
    ],
)
```

**TestSpec:**
```python
TestSpec(
    test_id="uart_echo",
    applies_to=["board", "bare_mcu"],
    requires_dut_features=["uart_console"],
    required_capabilities=[
        Requirement("uart", {"count": 1, "voltage_level": 3.3}),
    ],
    optional_capabilities=[],
)
```

### ExecutionPlan Output

**When compatible:**
```python
ExecutionPlan(
    executable=True,
    selected_instruments=["usb_uart_bridge"],
    matched_requirements=[...],
    missing_requirements=[],
    warnings=["No voltage measurement available; power validation skipped"],
    reasons=["DUT exposes 3.3V UART console and selected instrument supports it"],
)
```

**When not compatible:**
```python
ExecutionPlan(
    executable=False,
    selected_instruments=[],
    missing_requirements=["reset_control", "boot_mode_control"],
    reasons=[
        "flash_test requires programmable boot entry",
        "available instruments do not provide boot_mode_control",
    ],
    suggested_alternatives=["manual_boot_mode", "use stlink instrument"],
)
```

---

## 7. Static Compatibility vs Runtime Readiness

An important two-layer distinction:

| Layer | Question | Example |
|-------|----------|---------|
| Static compatibility | Theoretically can it work? | Instrument supports SWD |
| Runtime readiness | Can it work right now? | But not connected / firmware too old / port occupied |

**Principle:** Spec layer answers "should it be able to?" Runtime layer answers "can it right now?"

This distinction is extremely valuable for the doctor system.

---

## 8. Three Pitfalls to Avoid

### Pitfall 1: Hard-coded pair tables
```json
{
  "stm32_uart_test": ["usb_uart_bridge"],
  "flash_test": ["stlink"]
}
```
This works short-term but always breaks:
- New instruments can't be reused
- New tests require extending the table
- Parameterized capabilities can't be expressed
- Cannot explain "why incompatible"

Hard-coded tables may be used as cached views but should never be the ground truth.

### Pitfall 2: Scattering compatibility logic in UI / doctor / action handlers
Compatibility logic must be centralized. Otherwise doctor and dispatcher will have inconsistent behavior.

### Pitfall 3: Only boolean results, no explanation
The compatibility system must return reasons:
- Missing `boot_mode_control`
- Instrument only has 4 channels, test needs 8
- DUT voltage is 1.8V, instrument only supports 3.3V/5V
- Test requires programmable target, DUT marked `not_programmable`

---

## 9. Rollout Sequence

### Phase 1 — Test ↔ Instrument (highest value, easiest first)
- Each test declares `required_capabilities`
- Each instrument declares `provided_capabilities`
- Resolver does capability matching

Immediately improves: test planning, doctor, action availability, error messages, automatic instrument recommendation.

### Phase 2 — DUT ↔ Test
- DUT standard model adds: `kind / features / roles / exposed_interfaces / programmable_interfaces`
- Each test adds: `applies_to / requires_dut_features / excludes`
- Resolver adds DUT applicability checking

After this: AEL truly knows "what should be tested on this DUT."

### Phase 3 — DUT ↔ Instrument
Most complex, do last. Many DUT ↔ Instrument relationships can be indirectly inferred from Phases 1 and 2. Still has independent value for: connection planning, board bring-up, doctor wiring guidance, preflight check.

---

## 10. Spec Sections Summary

For reference when writing the formal spec:

1. **Goals** — make implicit compatibility explicit
2. **Scope** — DUT↔Test, Test↔Instrument, DUT↔Instrument; single and multi-instrument plans
3. **Core Concepts** — capability, requirement, constraint, compatibility result, execution plan
4. **Standard Object Extensions** — required fields for DUT, Test, Instrument
5. **Resolution Rules** — protocol match, count/resource match, voltage/electrical match, feature applicability, exclusion rules, fallback rules
6. **Explainability** — compatible/incompatible, reasons, missing capabilities, warnings, suggested alternatives
7. **Registry / Source of Truth** — single location for compatibility data
8. **Rollout Plan** — phased migration

---

*Extracted from AEL design discussion. Companion docs: `ael_board_dut_definition_spec_v0_1.md`*
