# ESP32JTAG Instrument API Completeness Checklist

Date: 2026-03-19

## Purpose

Define what "complete instrument API" means for `ESP32JTAG`, beyond the already
implemented minimal native API.

## Checklist

1. Identity is explicit.
- the instrument is named `ESP32JTAG`
- the device type is `multi_capability_instrument`
- it is not flattened into a single-purpose JTAG probe model

2. Capability families are explicit.
- `debug_remote`
- `reset_control`
- `capture_control`
- `preflight`

3. Status domains are explicit.
- `network`
- `gdb_remote`
- `web_api`
- `capture_subsystem`
- `monitor_targets`

4. Doctor output is subsystem-oriented.
- each domain has an individual result
- preflight data is preserved as evidence
- target enumeration is visible as part of doctor output

5. Runtime presentation is aligned.
- `instrument_view`
- `instrument_doctor`
- CLI describe/doctor output
all present `ESP32JTAG` as an instrument family, not only as a generic control probe

6. Ownership boundary is explicit.
- instrument API owns identity, capabilities, status, doctor, and preflight
- `esp32_jtag` backend owns execution actions

7. Lifecycle boundary is explicit.
- reachability and health are in scope
- provision / service restart / firmware update remain out of scope unless
  explicitly added later

8. Healthy live evidence exists.
- at least two healthy live doctor samples
- preferably across separate benches

9. Documentation is synchronized.
- closeout exists
- status note exists
- README milestone reflects current boundary

10. Skill/process capture exists.
- changes that expand this interface should end with closeout + skill capture

## Current State

As of this note:

- items `1-6` are implemented at a practical level
- item `7` is now explicitly documented
- item `8` has multiple healthy live samples
- items `9-10` are in place

So `ESP32JTAG` now has more than a minimal interface, but still does not expose
every possible lifecycle or execution action through the instrument API itself.
