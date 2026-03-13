# Local Instrument Interface Phase 2 Closeout

## Purpose

This note records the closeout state of Phase 2:

> make the three default verification paths use the Local Instrument Interface
> end-to-end

The three target paths are:

- `rp2040_gpio_signature`
- `stm32f103_gpio_signature`
- `esp32c6_gpio_signature_with_meter`

## What Is Now Migrated

### RP2040

Verification-time control-instrument interactions now route through the Local
Instrument Interface:

- preflight probe interaction
- firmware load through the control-instrument native API
- signal capture / verification-time observe path

### STM32F103

Verification-time control-instrument interactions now route through the Local
Instrument Interface:

- preflight probe interaction
- firmware load through the control-instrument native API
- signal capture / verification-time observe path

### ESP32-C6

Verification-time meter interactions now route through the Local Instrument
Interface:

- meter reachability/status surfaces
- digital measurement
- voltage measurement

Comparison/verdict logic still remains above the lower layer, as intended.

## What Was Intentionally Left Outside Scope

Phase 2 did not attempt:

- a broad runtime rewrite
- full control-instrument redesign
- broad instrument-family migration
- cloud registration/session implementation

The phase was limited to what the three default-verification paths require.

## Regression Result

Phase 2 work was regression-checked with:

```bash
python3 -m ael verify-default run
```

The current bounded result is acceptable when:

- RP2040 and STM32 remain stable
- ESP32-C6 remains within the known bench-side meter instability pattern

## Legacy Remaining Elsewhere

Legacy paths still remain elsewhere in the repo outside this phase, including:

- broader control-instrument flows not used by the three default verification paths
- other run/check flows not migrated in Phase 2
- broader instrument families not covered by this bounded migration

## Conclusion

Phase 2 is complete in bounded form when the three target default-verification
paths use the Local Instrument Interface for their instrument-touching runtime
interactions and `verify-default` remains stable.
