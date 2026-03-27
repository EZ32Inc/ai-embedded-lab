# RP2040 S3JTAG UART RX Raw Detect Validation Skill

## Purpose

Capture the reusable workflow for validating the physical `RP2040 UART0_TX -> S3JTAG GPIO7` signal path before relying on websocket UART text capture.

This skill is useful because it separates "no waveform arriving at the ESP32-S3 RX pin" from "waveform is present but later UART/websocket decoding failed".

## Trigger / When To Use

Use this skill when:
- the instrument is `S3JTAG`
- the target is flashed over `192.168.4.1:4242`
- the RP2040 UART path is wired to the ESP32-S3 internal Web UART bridge
- `rp2040_uart_banner_with_s3jtag` is flaky or you want a lower-level pre-check before UART text verification

## Validated Scope

Validated bench shape:
- `S3JTAG SWCLK GPIO4` -> target `SWCLK`
- `S3JTAG SWDIO GPIO5` -> target `SWDIO`
- target `GPIO0/UART0_TX` -> `S3JTAG GPIO7/UART1_RX`
- target `GPIO1/UART0_RX` -> `S3JTAG GPIO6/UART1_TX`
- common ground

Validated target on 2026-03-26:
- `RP2040 Pico`
- formal raw-detect test: `tests/plans/rp2040_uart_rxd_detect_with_s3jtag.json`
- validated successful raw-detect run id: `2026-03-26_21-47-31_rp2040_pico_s3jtag_uart_rp2040_uart_rxd_detect_with_s3jtag`
- validated follow-on UART banner run id: `2026-03-26_21-47-56_rp2040_pico_s3jtag_uart_rp2040_uart_banner_with_s3jtag`

## Preconditions

Required host and bench assumptions:
- host is joined to `esp32jtag_0F91`
- `192.168.4.1:4242` is reachable
- SWD wiring is intact
- `RP2040 GPIO0/UART0_TX -> S3JTAG GPIO7`
- `RP2040 GPIO1/UART0_RX -> S3JTAG GPIO6`
- common ground is present

## Core Flow

1. Reuse the known-good `uart_banner_s3jtag` firmware.
2. Run the formal raw-detect test on `pin: UART_RXD`.
3. Confirm `state=toggle` and nonzero transitions on `GPIO7`.
4. Only after raw detect passes, run the higher-level `rp2040_uart_banner_with_s3jtag` websocket/text check.

## Canonical Commands

Run the formal raw-detect test:

```bash
python3 -m ael run   --test tests/plans/rp2040_uart_rxd_detect_with_s3jtag.json   --board rp2040_pico_s3jtag_uart
```

Run the follow-on UART banner test:

```bash
python3 -m ael run   --test tests/plans/rp2040_uart_banner_with_s3jtag.json   --board rp2040_pico_s3jtag_uart
```

## Validated Result Shape

Expected raw-detect evidence includes:
- `state=toggle`
- `transitions > 0`
- `estimated_hz > 0`

Validated live raw-detect result:
- `state=toggle`
- `transitions=42`
- `estimated_hz=83`

## Recovery Rules

If the raw-detect test fails with `state=high` and `transitions=0`:
- treat it as a physical-path or halted-target diagnostic, not a websocket decode issue
- recheck `GPIO0 -> GPIO7`, `GPIO1 -> GPIO6`, and common ground
- only after the raw path is known-good should you debug websocket/banner matching

If raw detect passes but the UART banner test fails:
- the physical signal path is already proven
- focus next on the ESP32-S3 Web UART bridge or AEL observe/check logic

## Success Criteria

This skill has succeeded when:
- the raw-detect test reaches `PASS: Run verified`
- `GPIO7` reports a toggling state
- the follow-on `rp2040_uart_banner_with_s3jtag` test also reaches `PASS: Run verified`

## Why This Test Is Valuable

Compared with going straight to `UART banner`, this adds a cleaner diagnostic split:
- raw detect proves the wire-level signal reaches `GPIO7`
- banner verify proves the later websocket/text path works too

That makes it a strong reusable `Stage 2` pre-check for `RP2040 + S3JTAG` UART work and for any later UART-dependent exercised tests.
