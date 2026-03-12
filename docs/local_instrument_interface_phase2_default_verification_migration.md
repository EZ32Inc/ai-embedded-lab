# Local Instrument Interface Phase 2 Default Verification Migration

## Purpose

Phase 1 proved the Local Instrument Interface in bounded form.

Phase 2 has one narrower goal:

> Make the three default verification paths use the Local Instrument Interface
> end-to-end.

The three target paths are:

- `rp2040_golden_gpio_signature`
- `stm32f103_golden_gpio_signature`
- `esp32c6_golden_gpio`

This phase is intentionally limited.

It is **not**:

- a general runtime rewrite
- a universal instrument migration
- a broad orchestration redesign

Only the minimum work needed to move these three default-verification paths
onto the Local Instrument Interface should be implemented.

## Success Condition

At the end of this phase, all three default verification paths should satisfy:

```text
test
→ verification pipeline
→ Local Instrument Interface
→ instrument native API
→ real instrument implementation
```

For these three flows, no legacy adapter path should remain in the verification
path.

## Current Runtime Paths

### RP2040

Current path is still legacy control-instrument driven:

```text
default_verification
→ pipeline / adapter_registry
→ BMDA / esp32jtag-style adapter path
→ esp32jtag-backed control instrument
```

What is already present:

- control-instrument metadata selection
- control-instrument doctor/view surfaces

What is missing:

- native control-instrument API used end-to-end by verification

### STM32F103

Current path is the same class of legacy control-instrument path:

```text
default_verification
→ pipeline / adapter_registry
→ BMDA / esp32jtag-style adapter path
→ esp32jtag-backed control instrument
```

What is already present:

- control-instrument metadata selection
- control-instrument doctor/view surfaces

What is missing:

- native control-instrument API used end-to-end by verification

### ESP32-C6

Current path is closest to the Local Instrument Interface, but is still mixed:

```text
default_verification
→ pipeline / adapter_registry
→ meter TCP adapter + reachability helpers
→ real meter
```

What is already present:

- meter native API
- meter lower-layer metadata and action vocabulary

What is missing:

- routing verification-side meter actions through the native API instead of the
  legacy adapter path

## Target Runtime Paths

### RP2040 target

```text
default_verification
→ verification pipeline
→ Local Instrument Interface
→ control-instrument native API
→ esp32jtag-backed control instrument
```

### STM32F103 target

```text
default_verification
→ verification pipeline
→ Local Instrument Interface
→ control-instrument native API
→ esp32jtag-backed control instrument
```

### ESP32-C6 target

```text
default_verification
→ verification pipeline
→ Local Instrument Interface
→ meter native API
→ real meter implementation
```

## Minimal Native API Required

### Common metadata commands

These already exist in the lower-layer contract and should remain common:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`

### Meter-side native actions

These are already the relevant lower-layer actions for the ESP32-C6 path:

- `measure_digital`
- `measure_voltage`
- `stim_digital`

### Minimal control-instrument native actions

Only the minimum needed by the current default-verification tests should be
introduced.

Candidate commands:

- `identify`
- `get_status`
- `doctor`
- `reset_target`
- `observe_gpio`
- `capture_signature`

These commands should support the current RP2040 and STM32 default verification
flows without trying to generalize every control-instrument capability.

## Migration Boundaries

### Included

- routing verification-time instrument actions through the Local Instrument
  Interface
- minimal native control-instrument API required by RP2040 and STM32 default
  verification
- replacing legacy adapter usage in these three verification flows

### Explicitly not included

- broad instrument-family migration
- broad control-instrument redesign
- cloud registration/session implementation
- moving orchestration-level verification verdict logic into the lower layer
- blindly forcing flash/debug orchestration into the lower layer unless it is
  strictly required by the three target flows

## Important Boundary

The Local Instrument Interface should expose native actions only.

These remain above the lower layer:

- comparison logic
- signature-match verdict logic
- task-level pass/fail decisions
- default-verification orchestration logic

## Batch Order

### Batch 1

Write this migration doc and use it as the execution boundary.

### Batch 2

Migrate the ESP32-C6 path first.

Reason:

- it is already closest to the Local Instrument Interface
- meter native API already exists

### Batch 3

Define the minimal control-instrument native API required by the RP2040 and
STM32 default-verification flows.

### Batch 4

Migrate `rp2040_golden_gpio_signature` to the Local Instrument Interface.

### Batch 5

Migrate `stm32f103_golden_gpio_signature` using the same model.

### Batch 6

Write the closeout review and confirm that the three target flows are fully
migrated.

## Regression Gates

Because this phase touches active shared runtime paths, regression gates are
mandatory.

After each shared-runtime batch:

```bash
python3 -m ael verify-default run
```

Phase 2 is not complete unless:

- the three target flows use the Local Instrument Interface end-to-end
- `verify-default` remains stable
- no broader migration is attempted in the same phase

## Closeout Deliverable

At the end of the phase, create:

- `docs/local_instrument_interface_phase2_closeout.md`

That closeout should confirm:

- all three default-verification paths now use the Local Instrument Interface
  end-to-end
- legacy adapter paths were removed from these three flows
- what still remains legacy elsewhere in the repo
