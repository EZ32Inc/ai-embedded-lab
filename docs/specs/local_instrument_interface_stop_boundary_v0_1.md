# Local Instrument Interface Stop Boundary v0.1

## Purpose

This note records where the current local-instrument-layer work should stop for now.

It exists to prevent bounded lower-layer work from drifting into a broad runtime rewrite.

## Established

The following are now established:

- USB-UART bridge as the strongest lower-layer pilot
- meter path as an additive lower-layer follow-on
- native metadata command vocabulary:
  - `identify`
  - `get_capabilities`
  - `get_status`
  - `doctor`
- capability-specific action command vocabulary
- shared visibility through:
  - manifests
  - `instrument_view`
  - `instrument_doctor`

## Additive But Not Broadly Integrated

The following now exist, but are still intentionally bounded:

- meter native action mapping
- native API dispatch for selected lower-layer consumers
- lower-layer visibility in current inspection surfaces

## Deferred

The following remain deferred:

- broad verification-runtime rewiring around the native API
- control-instrument/JTAG normalization into the same lower-layer contract
- cloud-facing registration/session implementation
- broad instrument-family migration

## Practical Rule

Current practical rule:

- additive lower-layer work is acceptable
- shared-surface changes require regression checks
- broad runtime unification is out of scope until a later explicit phase

## Conclusion

Current lower-layer work is strong enough to stop and hold the boundary.

The next phase should be chosen intentionally rather than reached by drift.
