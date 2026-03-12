# Local Instrument Interface Control-Instrument Applicability Review v0.1

## Purpose

This note reviews whether current control-instrument / JTAG-style paths should adopt the same Local Instrument Interface shape used by the first USB-UART bridge pilot.

It is a bounded review note.
It does not change current control-instrument runtime behavior.

## Current Control-Instrument Reality

Current control-instrument paths are centered on:

- explicit config-bound instances
- adapter-driven runtime behavior
- SWD/JTAG-oriented operations
- BMDA/OpenOCD/GDB-style control flows

Examples:

- `esp32jtag_rp2040_lab`
- `esp32jtag_stm32_golden`

## What Already Fits the Lower-Layer Model

Control instruments already have:

- stable instance identity
- communication metadata
- capability surfaces
- doctor/view support

So they already satisfy some lower-layer requirements.

## What Does Not Yet Fit Cleanly

The current control-instrument path is less suited to the first native-interface profile because:

- action semantics are still closely coupled to adapter/runtime behavior
- some operations are toolchain-mediated rather than direct instrument commands
- flashing/debugging are not yet shaped as small reusable native actions
- current working flows are already stable and should not be risked early

## Conclusion

Reasonable current conclusion:

- control instruments should not be the next immediate native-interface implementation target
- they are a later design target after the bridge pilot and any bounded meter follow-on are better understood

## Recommended Next Step

For now:

- keep control-instrument review architectural and observational
- do not force runtime unification in the current phase

## Current Boundary

Current intended boundary is:

- USB-UART bridge:
  - implemented as the first lower-layer pilot
- meter path:
  - additive lower-layer follow-on now exists
- control instruments:
  - still review-only in this phase

That boundary should remain stable until there is a stronger reason to normalize control-instrument actions.
