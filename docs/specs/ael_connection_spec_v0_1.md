# AEL Connection Specification v0.1

## One-sentence definition

**A connection is the bench-level DUT ↔ Instrument relationship description AEL uses to understand wiring, signal roles, and setup assumptions for a run.**

---

## 1. Purpose

This document defines the real AEL **Connection** part from the 6-part architecture.

In AEL terms, Connection is **ConnA**, not instrument communication access.

This spec exists to clarify:

- how DUT and Instrument are physically and logically related on the bench
- how current AEL represents wiring and signal-role assumptions
- what setup facts are needed for safe and meaningful execution
- what should be shown in inventory, explain, and summary output

This spec is intended to support:

- wiring clarity
- signal-role clarity
- safer execution
- better describe-test / explain-stage output
- better setup summaries and archived setup facts

It is **not** intended to define:

- Wi-Fi / TCP / HTTPS / GDB access to an instrument
- endpoint normalization
- auth/options normalization
- a runtime communication/session framework

Those belong to the instrument-internal communication-access layer, not to Connection.

---

## 2. Position in the AEL architecture

This specification defines the top-level **Connection** part in the AEL architecture.

### Bench

In this document, **Bench** means the concrete execution setup in which a DUT and one or more instruments are physically arranged and connected for a run.

Bench includes the relevant:

- wiring
- connected observation and control paths
- setup assumptions that make a specific validation meaningful

Bench is an important contextual concept for Connection, but it is **not** a separate top-level architecture part.

### Important distinction

#### AEL Connection (ConnA)
Connection means the **DUT ↔ Instrument relationship layer**.

It includes:

- physical wiring
- pin mapping
- signal roles
- observation paths
- control paths
- voltage and grounding assumptions
- setup constraints such as `NC`, shared nets, and expected bench topology

#### Instrument Communication Access (ConnB)
Instrument communication access means how Orchestration reaches one selected surface of an instrument at runtime.

Examples:

- ESP32JTAG GDB remote
- ESP32JTAG web API
- meter TCP surface

That is part of **Instrument**, not Connection.

---

## 3. Scope

This draft applies to bench-visible DUT ↔ Instrument relationship facts in current AEL.

Current code-reality examples include:

- board `default_wiring`
- board `bench_connections`
- test-plan `bench_setup`
- legacy test-plan `connections`
- `observe_map` and `verification_views` as resolved observation intent

This draft does not yet attempt to model:

- full electrical-rule validation
- automatic voltage-domain reasoning
- generic netlist modeling
- dynamic rewiring
- a complete bench-topology language

The goal in v0.1 is smaller: describe the current AEL connection layer clearly enough to guide metadata, summaries, and future refinement.

---

## 4. Current AEL code reality

Current AEL already has a practical connection model, even though it is spread across a few config shapes.

### 4.1 Board-side connection facts

Board configs currently hold:

- `default_wiring`
  - coarse required wiring facts for the run path
  - examples: `swd`, `reset`, `verify`
- `bench_connections`
  - explicit DUT pin to instrument/bench point mappings
- `observe_map`
  - symbolic observation aliases such as `sig` or `led`
- `verification_views`
  - named verification interpretations of those aliases

Examples:

- [stm32f103.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/boards/stm32f103.yaml)
- [stm32f401rct6.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/boards/stm32f401rct6.yaml)

### 4.2 Test-plan connection facts

Test plans currently hold bench-specific connection intent through:

- `bench_setup`
- legacy `connections`

These are currently used most clearly for meter-backed paths such as:

- [esp32c6_gpio_signature_with_meter.json](/nvme1t/work/codex/ai-embedded-lab/tests/plans/esp32c6_gpio_signature_with_meter.json)

Current `bench_setup` shapes include:

- `dut_to_instrument`
- `dut_to_instrument_analog`
- `ground_required`

### 4.3 Runtime usage today

Current AEL already uses connection facts in several places:

- strategy resolution merges `default_wiring` with CLI wiring overrides
- missing required coarse wiring is normalized to `UNKNOWN`
- verify steps use resolved wiring such as `verify=P0.0`
- summaries and last-known-good output include `wiring_assumptions`
- inventory `describe-test` renders explicit `connections`
- inventory warns on suspicious duplicate observation mappings
- stage explain includes resolved wiring assumptions

Relevant current code paths:

- [strategy_resolver.py](/nvme1t/work/codex/ai-embedded-lab/ael/strategy_resolver.py)
- [inventory.py](/nvme1t/work/codex/ai-embedded-lab/ael/inventory.py)
- [stage_explain.py](/nvme1t/work/codex/ai-embedded-lab/ael/stage_explain.py)
- [pipeline.py](/nvme1t/work/codex/ai-embedded-lab/ael/pipeline.py)

---

## 5. Core model

The current AEL connection layer is best understood as two related levels:

1. **Coarse execution wiring**
2. **Explicit bench connection mapping**

### 5.1 Coarse execution wiring

This is the minimum wiring needed for a run path to make sense.

Current examples:

- `swd`
- `reset`
- `verify`

This level is small and operational. It answers questions like:

- where is SWD expected?
- is reset wired or intentionally `NC`?
- which instrument point is used for generic verify capture?

### 5.2 Explicit bench connection mapping

This is the more detailed relationship description used for understanding and explaining the setup.

It answers questions like:

- which DUT pin is connected to which probe input?
- which DUT signal is expected to toggle, stay high, or stay low?
- is there a required analog path?
- is shared ground required?
- are multiple observation points attached to the same MCU pin?

---

## 6. Minimum connection metadata

The minimum current AEL connection model should stay small.

Recommended core concepts:

- `default_wiring`
- `bench_connections`
- `bench_setup`
- `observe_map`
- `verification_views`

### 6.1 `default_wiring`

`default_wiring` is the coarse per-board execution assumption block.

Current examples:

```yaml
default_wiring:
  swd: P3
  reset: NC
  verify: P0.0
```

This block is important because current run planning and verification directly depend on it.

### 6.2 `bench_connections`

`bench_connections` is the board-level list of explicit DUT ↔ bench mappings.

Current example:

```yaml
bench_connections:
  - from: PA4
    to: P0.0
  - from: PA5
    to: P0.1
  - from: PC13
    to: LED
```

This is the clearest current form for human-readable connection description.

### 6.3 `bench_setup`

`bench_setup` is the test-plan-level connection assumption block.

It is useful where the relationship is more scenario-specific than board-static, especially meter-backed validation.

Current example:

```json
{
  "bench_setup": {
    "dut_to_instrument": [
      {"dut_gpio": "X1(GPIO4)", "inst_gpio": 11, "expect": "toggle", "freq_hz": 1000}
    ],
    "dut_to_instrument_analog": [
      {"dut_signal": "3V3", "inst_adc_gpio": 4, "expect_v_min": 2.8, "expect_v_max": 3.45}
    ],
    "ground_required": true
  }
}
```

### 6.4 `observe_map` and `verification_views`

These are not pure connection lists, but they are part of the current practical connection model because they explain how connection facts support verification intent.

`observe_map`:

- maps symbolic verification names to instrument-facing observation points

`verification_views`:

- describes named interpretations such as `signal` or `led`

Together they help translate:

- physical bench mapping
- into machine-observed verification semantics

---

## 7. Normalized connection description

At runtime, AEL may normalize connection-related metadata into a compact description for planning, summaries, inventory, or archive output.

This should remain a helper description, not a heavy bench-topology framework.

### 7.1 Suggested normalized fields

Useful normalized fields include:

- `board`
- `instrument_instance` or `instrument_id`
- `default_wiring`
- `connections`
- `verification_views`
- `warnings`
- `source`

Optional fields:

- `ground_required`
- `analog_paths`
- `notes`

### 7.2 Source precedence

Current AEL effectively resolves connection facts from several layers:

1. CLI wiring override
2. board `default_wiring`
3. board `bench_connections`
4. test-plan `bench_setup`
5. legacy test-plan `connections`

Not every run uses every layer, but the spec should acknowledge that the current model is assembled rather than coming from a single source block.

---

## 8. Connection semantics

To keep Connection useful without over-design, v0.1 should focus on a few concrete semantic categories.

### 8.1 Control wiring

Examples:

- SWD
- reset
- boot control if needed later

These are about controlling the DUT or enabling flash/debug workflows.

### 8.2 Observation wiring

Examples:

- `verify -> P0.0`
- `PA4 -> P0.0`
- `PC13 -> LED`

These are about observing DUT behavior through an instrument or bench-visible point.

### 8.3 Expected behavior on a connection

Especially in plan-level `bench_setup`, a connection may include expected behavior such as:

- `toggle`
- `high`
- `low`
- expected frequency range
- expected voltage range

This is important because current AEL test plans already combine connection facts and expected observable behavior.

### 8.4 Setup constraints

Examples:

- `NC`
- `ground_required`
- duplicate observation mappings that deserve warnings

These are not just comments. They affect whether a run is safe and whether results are trustworthy.

---

## 9. Diagnostics and warnings

One reason to define Connection more clearly is to improve setup diagnostics.

Current and near-current useful warning kinds include:

- missing coarse wiring
- duplicate observation mappings
- required ground not confirmed
- ambiguous verify mapping
- unsupported or unknown connection keys

Suggested minimal diagnostic shape:

- `ok`
- `warnings`
- `missing`
- `connection_summary`

This should be used first for:

- inventory
- explain-stage
- doctor-style setup checks later

It should not require a full electrical-rule engine in v0.1.

---

## 10. Mapping to current AEL examples

### 10.1 STM32F103 / STM32F401 probe-based GPIO validation

Current board configs already express Connection through:

- `default_wiring`
- `bench_connections`
- `observe_map`
- `verification_views`

For example:

- SWD control path on `P3`
- reset intentionally `NC`
- generic verify path on `P0.0`
- explicit DUT GPIO mappings to `P0.x`
- LED or signal observation paths

This is a strong current example of ConnA.

### 10.2 ESP32-C6 meter-backed GPIO validation

Current test plans express Connection through:

- `bench_setup.dut_to_instrument`
- `bench_setup.dut_to_instrument_analog`
- `ground_required`

This is another strong current example of ConnA, because it describes the DUT ↔ Instrument relationship, not how Orchestration reaches the meter over TCP.

---

## 11. Implementation guidance

A practical first implementation path for ConnA should be:

1. keep this metadata-first
2. stabilize current connection shapes rather than inventing a new universal one
3. improve inventory / describe-test / explain-stage output around resolved connection facts
4. improve warnings and setup diagnostics
5. archive resolved connection facts more explicitly where useful

Only later:

6. consider a more normalized `bench_setup` / `connection` model
7. consider lightweight validation for common connection mistakes
8. consider explicit voltage-domain metadata if there is a real operational need

Not yet:

- a full topology language
- netlist-style modeling
- automatic electrical reasoning
- dynamic bench reconfiguration

---

## 12. Explicit non-goals for v0.1

This draft does not define:

- instrument communication access
- endpoint normalization
- protocol selection
- auth/options resolution
- a universal runtime connection/session layer
- a seventh architecture part

It also does not attempt to fully unify every current connection-like field into one schema in v0.1.

That unification may come later, but the immediate goal is a clear and code-reality-aligned ConnA definition.

---

## 13. Summary

The purpose of `ael_connection_spec_v0_1` is to define the real AEL **Connection** part:

- the DUT ↔ Instrument relationship layer
- wiring and signal-role assumptions
- observation and control paths
- setup constraints that matter for safe and meaningful runs

This spec should help AEL:

- describe current bench setups more clearly
- explain runs more accurately
- warn about bad or incomplete setup assumptions
- prepare for later refinement of the connection model

without turning Connection into:

- instrument communication access
- a runtime transport framework
- a heavy topology system too early
