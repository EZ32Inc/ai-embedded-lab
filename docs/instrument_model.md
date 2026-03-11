# AEL Instrument Model

## 1. Purpose

This document defines the intended instrument model for AEL and explains how the current repository maps onto that model.

Its goals are:
- make the hardware-control model explicit
- reduce confusion between `instrument` and `probe`
- document confirmed current behavior separately from target architecture
- guide future refactoring toward a simpler, capability-based model

This is a durable design document, not a session note.

## 2. Core Position

The preferred AEL architecture is:

- `instrument` is the canonical hardware abstraction
- `probe` is not a separate top-level category
- a probe is an instrument subtype, or more precisely, an instrument with capabilities such as flash, debug, reset, and observe

In practical terms:
- a meter is an instrument
- an ESP32JTAG adapter is an instrument
- a future scope, power switch, relay controller, or UART monitor is also an instrument

The long-term direction should therefore be:
- stop expanding `probe` as a parallel architecture concept
- retain `probe` only as legacy vocabulary where needed for compatibility or transitional clarity

## 3. Why This Matters

Keeping `probe` and `instrument` as parallel concepts creates avoidable ambiguity:

- binding logic becomes harder to reason about
- stage explanation can describe the wrong bench model
- resource locking can serialize unrelated work if legacy probe assumptions leak in
- board configuration grows duplicate concepts for hardware selection
- future instruments have no single, consistent model to fit into

A unified instrument model better matches the real bench:
- AEL uses hardware endpoints with capabilities
- tasks depend on those capabilities
- resource ownership should follow real hardware identity and endpoint sharing

## 4. Confirmed Current Repo State

The current repository is already partially aligned with the unified model.

Confirmed:
- instrument manifests and registry lookup already exist in `ael/instruments/*`
- instrument selection for meter-backed tests already exists through `test.instrument` and `resolve_instrument_context()`
- capability and communication metadata already exist for both manifest-backed instruments and probe bindings
- default verification resource locking already treats instrument endpoint sharing as a resource class
- stage explanation already reports both probe-related and instrument-related capability surfaces

Also confirmed:
- some code paths still use `probe` as a separate runtime/config concept
- board config policy still includes fields such as `probe_required`, `probe_config`, and `allow_legacy_probe_fallback`
- `instrument_instance` in board config currently selects what is operationally a probe-like instrument instance
- `config_resolver.py` still exposes `resolve_probe_config()` and `resolve_probe_instance()`
- some compatibility payloads still emit `probe*` fields alongside the newer control-instrument structures

So the repo is not missing an instrument model.
It has a partially unified instrument model with legacy probe-specific seams.

## 5. Current Operational Model

Today, AEL effectively has two related but not fully unified hardware-selection paths.

### A. Manifest-backed instrument path

Used mainly for meter-backed verification.

Typical properties:
- selected from `test.instrument` or `board.instrument`
- resolved via `InstrumentRegistry`
- carries manifest-defined transport, communication, and capability metadata
- used for capabilities such as:
  - `measure.digital`
  - `measure.voltage`
  - `stim.digital`

Example:
- `esp32s3_dev_c_meter`

### B. Probe-binding path

Used mainly for flash/debug/observe behavior tied to debug-adapter-style hardware.

Typical properties:
- selected through board policy or CLI override
- resolved via `probe_config` or `instrument_instance`
- loaded through `probe_binding`
- carries connection, communication, and capability-surface metadata

Typical capabilities exposed through this path:
- `swd`
- `gpio_in`
- `gpio_out`
- `adc_in`
- `reset_out`

Example:
- `esp32jtag_stm32_golden`

### What this means

Operationally, both paths already represent instruments.
They differ mostly in how they are described and resolved, not in what they fundamentally are.

## 6. Recommended Canonical Model

The target model should be capability-first:

- a task requests one or more capabilities
- AEL binds those capabilities to one or more instrument instances
- the selected instrument instances provide transport, communication, and capability surfaces
- locking and explanation are derived from those real bindings

Under this model:
- `probe` becomes a descriptive label for some instrument profiles
- `probe_required` becomes a statement about required instrument capabilities, not a separate object class
- `instrument_instance` becomes the standard explicit instance-binding mechanism

Recommended conceptual layers:

1. Instrument identity
- stable instance id
- physical or network identity

2. Communication and transport
- USB, serial, TCP, Wi-Fi, web API, GDB remote, etc.

3. Capability surfaces
- what the instrument can do and through which surface

4. Task binding
- which task uses which instrument instance for which capability

5. Resource ownership
- which physical or endpoint-level resources must be locked

## 7. Policy Implications

If AEL adopts `instrument` as the only canonical concept, several policy decisions follow.

### Explicit binding is preferred

Use explicit instance or explicit config selection whenever practical.

Reason:
- it reflects the real bench model
- it reduces hidden fallback behavior
- it makes explanation and locking more trustworthy

### Legacy implicit probe fallback should shrink over time

Legacy fallback may remain for compatibility, but it should be treated as transitional behavior.

Reason:
- it can introduce hidden shared-resource assumptions
- it is weaker than explicit instrument binding

### No implicit binding is a valid state

Some tasks should proceed without an implicitly attached debug-style instrument.

This means:
- lack of an implicit probe is not necessarily a configuration bug
- the task may rely on a different instrument path, or on no external instrument for some stages

## 8. Recommended Migration Direction

The migration should be controlled, not a blind rename.

### Phase 1: Documentation and naming discipline

- document `instrument` as the canonical architecture term
- describe `probe` as legacy or capability-profile vocabulary
- stop introducing new top-level `probe` abstractions

### Phase 2: Resolver unification

- evolve resolver logic from `resolve_probe_*` toward generic instrument-binding helpers
- keep compatibility wrappers where needed
- make returned metadata consistently instrument-shaped

### Phase 3: Config cleanup

- prefer explicit instrument instance/config binding
- gradually replace probe-only config semantics with capability-oriented instrument semantics
- retain compatibility fields only where necessary

### Phase 4: Explanation and reporting cleanup

- report selected hardware primarily as instruments and capabilities
- keep probe-specific wording only as a secondary explanatory alias when useful
- prefer structured control-instrument objects over duplicated flat legacy fields

### Phase 5: Runtime simplification

- unify lock-key derivation, diagnostics, and stage planning around instrument bindings
- reduce code that branches primarily on `probe` versus `instrument`

## 9. Confirmed Constraints and Reasonable Interpretation

### Confirmed

- the current repo already supports instruments beyond debug probes
- the current repo already stores capability and communication metadata for both manifest-backed instruments and probe-like instances
- the current execution model depends on real hardware/resource identity more than on the word `probe`

### Reasonable interpretation

- the remaining split is mostly architectural debt from historical growth
- the system can be made simpler by converging on instrument-first language and APIs

### Open questions

- should `probe_required` become a capability requirement field, or remain temporarily as a compatibility alias
- how much compatibility policy should stay in `config_resolver.py`
- whether `probe_binding` should remain a separate loader or become an instrument-instance loader internally

## 10. Related Files

- [docs/instruments.md](/nvme1t/work/codex/ai-embedded-lab/docs/instruments.md)
- [ael/instruments/registry.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/registry.py)
- [ael/strategy_resolver.py](/nvme1t/work/codex/ai-embedded-lab/ael/strategy_resolver.py)
- [ael/config_resolver.py](/nvme1t/work/codex/ai-embedded-lab/ael/config_resolver.py)
- [ael/stage_explain.py](/nvme1t/work/codex/ai-embedded-lab/ael/stage_explain.py)
- [configs/instrument_instances/esp32jtag_stm32_golden.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/instrument_instances/esp32jtag_stm32_golden.yaml)
- [configs/boards/esp32c6_devkit.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/boards/esp32c6_devkit.yaml)
- [docs/skills/probe_fallback_policy.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/probe_fallback_policy.md)
- [docs/control_instrument_compatibility.md](/nvme1t/work/codex/ai-embedded-lab/docs/control_instrument_compatibility.md)

## 11. Short Guidance

When reasoning about new AEL architecture work:
- think in terms of instruments and capabilities
- treat `probe` as a legacy-specialized label, not a parallel top-level model
- prefer explicit instrument binding over hidden fallback
- derive locking and explanation from real instrument ownership, not historical naming
