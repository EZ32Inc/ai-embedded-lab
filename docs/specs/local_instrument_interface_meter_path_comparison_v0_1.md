# Local Instrument Interface Meter Path Comparison v0.1

## Purpose

This note compares the current meter-backed instrument path with the first Local Instrument Interface pilot implemented on `usb_uart_bridge_daemon`.

It is a bounded review note.
It does not migrate the meter runtime.

## Current Pilot Baseline

The current lower-layer pilot is the USB-UART bridge daemon.

What it now demonstrates:

- stable instrument identity
- doctor/status behavior
- machine-readable capability metadata
- a small native interface profile
- metadata commands:
  - `identify`
  - `get_capabilities`
  - `get_status`
  - `doctor`
- action commands:
  - `open`
  - `close`
  - `write_uart`
  - `read_uart`

## Current Meter Path

The current meter-backed path is represented mainly by:

- manifest-backed instrument metadata
- meter reachability and readiness helpers
- meter-specific adapter/provision functions
- orchestration-side verify branching in `pipeline.py`

Examples:

- `esp32s3_dev_c_meter`
- `ael.instruments.provision`
- `ael.adapters.esp32s3_dev_c_meter_tcp`

## What Already Aligns

The meter path already shares several important lower-layer properties with the pilot:

- manifest-backed instrument identity
- declared communication metadata
- declared capability surfaces
- doctor/reachability logic
- clear network-facing endpoint

This means the meter path is not alien to the Local Instrument Interface idea.

## What Now Aligns in the Current Repo

The current repo now has an additive meter-native layer in:

- `ael.instruments.meter_native_api`

That layer now exposes:

- `identify`
- `get_capabilities`
- `get_status`
- `doctor`
- `measure_digital`
- `measure_voltage`
- `stim_digital`

So the meter path is no longer only a comparison target.
It is now a bounded follow-on pilot.

## What Does Not Yet Align

The meter path is still less normalized than the bridge pilot in a few ways:

- metadata commands are not exposed as one explicit native interface profile
- doctor/reachability behavior is still partly helper-specific rather than expressed as one clean native API layer
- action semantics are mixed with orchestration assumptions
- verify-stage behavior is still closely tied to higher-level pipeline logic

Most importantly:

- the meter path is still optimized for a concrete verification flow
- the bridge pilot remains the cleaner reusable lower-layer baseline

## What Should Be Reused Later

If the meter path is normalized later, the safe reuse targets are:

1. metadata command shape
   - `identify`
   - `get_capabilities`
   - `get_status`
   - `doctor`

2. response/error model discipline
   - structured success
   - structured error
   - explicit retryable vs non-retryable meaning

3. capability-first native actions
   - measurement and stimulation actions should be raw/native
   - verification verdicts should stay above the lower layer

## What Should Not Be Forced Yet

The meter path should not be rewritten just to match the bridge pilot cosmetically.

The current repo depends on the meter path in:

- default verification
- degraded-instrument classification
- current bench diagnostics

So any future meter normalization should remain:

- additive first
- compatibility-preserving
- guarded by live `verify-default` regression checks

## Conclusion

Reasonable current conclusion:

- the USB-UART bridge was the right first pilot
- the meter path is now a bounded additive follow-on pilot
- higher-level verification logic should still remain above the lower layer
