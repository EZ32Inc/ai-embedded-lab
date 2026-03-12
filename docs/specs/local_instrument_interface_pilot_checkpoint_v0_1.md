# Local Instrument Interface Pilot Checkpoint v0.1

## Purpose

This document records what the first bounded Local Instrument Interface pilot has established in the current repository.

It is a checkpoint note, not a broad roadmap.

## Pilot Target

The first bounded pilot target was:

- `usb_uart_bridge_daemon`

This was chosen because it already had:

- stable identity handling
- a network-facing API
- list/select/show/doctor behavior
- direct read/write/open/close semantics

## What Is Now Proven

The pilot now proves that AEL can expose a lower local instrument-facing layer with:

- a bounded native interface profile
- explicit metadata commands
- explicit native action commands
- stable identity and doctor behavior
- compatibility with current manifest/view/doctor surfaces

## Native Interface Shape

The current bridge pilot now exposes a lower-layer native profile with:

- protocol:
  - `ael.local_instrument.native_api.v0.1`
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

## Shared-Surface Integration

The pilot is now visible through current shared AEL surfaces:

- instrument manifest metadata
- `instrument_view`
- `instrument_doctor`

This means the lower-layer pilot is not just bridge-local code; it is also visible through normal AEL instrument inspection paths.

## Regression Result

Because shared instrument surfaces were touched, the required regression gate was:

```bash
python3 -m ael verify-default run
```

At this checkpoint, that regression gate passed.

So the pilot did not regress the current default-verification path.

## What Is Still Out of Scope

This pilot does not yet prove:

- meter-path normalization into the same lower-layer API
- control-instrument/JTAG-path normalization into the same lower-layer API
- cloud registration/session implementation

Those remain later follow-on work.

## Recommended Next Decision

The next decision should be one of:

1. stop here and keep the bridge pilot as the proven lower-layer example
2. start a bounded meter-path normalization review

The safer immediate choice is still:

- treat the bridge pilot as the established baseline
- approach the meter path only as a bounded, regression-gated follow-on
