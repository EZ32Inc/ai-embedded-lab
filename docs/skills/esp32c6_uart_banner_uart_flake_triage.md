# ESP32-C6 UART Banner UART Flake Triage

Use this when `esp32c6_uart_banner` or a similar ESP32 UART-banner validation path fails intermittently after flash succeeds.

## Problem Shape

Typical failure signature:

- `flash` succeeds
- `instrument.signature` may still be healthy
- `check_uart` fails with `uart_expected_patterns_missing`
- `uart_observe.json` shows `bytes=0`, `lines=0`
- expected banner such as `AEL_READY ESP32C6 UART` is missing

## First Questions

1. Did flash actually succeed?
2. Did UART observe capture any bytes at all?
3. Is the failing run using the same concrete serial port as the last known good run?
4. Is the path failing at flash, or only later at UART observe?

## Recommended Retrieval

Start with:

```bash
PYTHONPATH=. python3 -m ael verify-default run --file /tmp/default_verification_meter_banner_single.json
```

Then inspect:

- `runs/<run_id>/result.json`
- `runs/<run_id>/uart_observe.json`
- `runs/<run_id>/flash.json`
- `runs/<run_id>/observe_uart.log`
- `runs/<run_id>/artifacts/run_plan.json`
- `runs/<run_id>/config_effective.json`

## What To Compare

Compare the failing run against a last known good banner run.

Focus on:

- `flash.json.port`
- `uart_observe.json.bytes`
- `uart_observe.json.lines`
- `uart_observe.json.missing_expect`
- whether `observe_uart.log` is empty or contains boot/application lines
- whether `run_plan.json` shows a concrete UART port or a symbolic one

## Important Interpretation Rule

If the failure run shows:

- `flash` success
- `uart_observe.json.bytes = 0`
- `observe_uart.log` empty

then this is usually not a schema problem and not automatically a firmware logic bug.

Treat it first as a UART acquisition/runtime-timing problem.

## Current Repo Behavior

The repo now hardens this path in two places:

1. `bench_setup.serial_console` is propagated into `observe_uart_cfg` during UART step construction.
2. Symbolic ports such as `auto_usb_serial_jtag` are resolved through `flash.json.port` inside `check_uart` when available.

This means future failures should be interpreted after that contract is taken into account.

## Practical Next Actions

If the path fails once:

1. Rerun the same banner single-run once more.
2. Compare the new run with the last known good run.
3. If the second run passes, classify it as a likely flake and keep the artifacts.

If the path fails repeatedly with `0 bytes / 0 lines`:

1. Inspect capture timing and post-flash settle assumptions.
2. Check whether USB-Serial/JTAG is re-enumerating or becoming unavailable between flash and observe.
3. Consider adding or adjusting UART settle timing rather than changing banner strings or schema metadata.

## What Not To Conclude Too Early

Do not immediately conclude that:

- schema metadata is wrong
- the banner string is wrong
- the firmware never starts

A successful earlier or later run with the same firmware is strong evidence against those conclusions.
