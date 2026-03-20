# Instrument Interface Gap Matrix 2026-03-20

## Purpose

Record the current standardization state of the four active instrument families
under the unified provider/interface model.

Families in scope:

- `stlink`
- `esp32jtag`
- `esp32_meter`
- `usb_uart_bridge`

## Current Standardized Boundary

All four families now participate in the same provider-registry structure:

- [interfaces/base.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/interfaces/base.py)
- [interfaces/registry.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/interfaces/registry.py)
- [interfaces/stlink.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/interfaces/stlink.py)
- [interfaces/esp32jtag.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/interfaces/esp32jtag.py)
- [interfaces/esp32_meter.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/interfaces/esp32_meter.py)
- [interfaces/usb_uart_bridge.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/interfaces/usb_uart_bridge.py)

Active callers now route through that structure in:

- [native_api_dispatch.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/native_api_dispatch.py)
- [instrument_doctor.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_doctor.py)
- [instrument_view.py](/nvme1t/work/codex/ai-embedded-lab/ael/instrument_view.py)

## Gap Matrix

| Family | Unified metadata contract | Unified provider path | Family-owned action surface | Doctor/status through provider | Remaining gap |
| --- | --- | --- | --- | --- | --- |
| `stlink` | yes | yes | partial | yes | backend actions such as `reset` and `debug_read_memory` are still not surfaced through a wider native dispatch vocabulary |
| `esp32jtag` | yes | yes | mostly yes | yes | legacy `control_instrument_native_api` still exists as an implementation detail under the JTAG family-owned wrappers |
| `esp32_meter` | yes | yes | yes | yes | native API file still sits outside the new `interfaces/` directory as an implementation module rather than being fully renamed/re-homed |
| `usb_uart_bridge` | yes | yes | partial | yes | action execution is now wrapped through the daemon HTTP surface, but this path has not yet been integrated into broader runtime consumers |

## What Is Now Consistent

Across all four families, AEL now has a consistent top-level concept for:

- metadata commands
  - `identify`
  - `get_capabilities`
  - `get_status`
  - `doctor`
- provider-based family resolution
- family-owned native interface profile
- family-specific health domains carried inside a common top-level contract

## What Is Still Intentionally Uneven

The system is not yet trying to force the same action set on every family.
That remains intentional.

Differences that are still valid:

- `stlink` is a local debug probe
- `esp32jtag` is a multi-capability control instrument
- `esp32_meter` is a measurement/stimulation instrument
- `usb_uart_bridge` is a UART bridge service

The standardization goal is common interface shape, not identical capability sets.

## Next Recommended Cleanup

The next cleanup pass should target two things:

1. reduce old implementation-file prominence
   - keep `*_native_api.py` as implementation detail
   - continue moving AI-facing contract thinking into `interfaces/`
2. widen standardized action dispatch gradually
   - only where there is a concrete consumer and stable capability advertisement

## Current Conclusion

The repo now has one real instrument-interface spine rather than several
family-specific partial patterns.

That does not mean the migration is fully complete.
It does mean new instrument work can now be expected to enter through one
standardized provider contract instead of inventing another special path.
