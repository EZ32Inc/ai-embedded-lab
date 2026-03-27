# RP2040 S3JTAG GPIO Interrupt Validation Skill

## Purpose

Capture the reusable workflow for validating a local `GPIO16 -> GPIO17` interrupt loopback on `RP2040` through the `S3JTAG` bench.

This skill is useful because it validates more than a raw signal toggle: it proves the RP2040 can generate edges, receive them on a second pin, and count them through the interrupt subsystem.

## Trigger / When To Use

Use this skill when:
- the instrument is `S3JTAG`
- the target is flashed over `192.168.4.1:4242`
- you want a `Stage 2` exercised interrupt test instead of only signal-level observation
- the UART path has already been validated well enough to trust bounded PASS/FAIL reporting

## Validated Scope

Validated bench shape:
- `S3JTAG SWCLK GPIO4` -> target `SWCLK`
- `S3JTAG SWDIO GPIO5` -> target `SWDIO`
- target `GPIO16` -> target `GPIO17`
- target `GPIO0/UART0_TX` -> `S3JTAG GPIO7/UART1_RX`
- target `GPIO1/UART0_RX` -> `S3JTAG GPIO6/UART1_TX`
- common ground

Validated target on 2026-03-26:
- `RP2040 Pico`
- formal test: `tests/plans/rp2040_gpio_interrupt_loopback_with_s3jtag.json`
- validated successful run id: `2026-03-26_21-51-08_rp2040_pico_s3jtag_uart_rp2040_gpio_interrupt_loopback_with_s3jtag`

## Preconditions

Required host and bench assumptions:
- host is joined to `esp32jtag_0F91`
- `192.168.4.1:4242` is reachable
- SWD wiring is intact
- `GPIO16 -> GPIO17` jumper is present
- `GPIO0 -> GPIO7` and `GPIO1 -> GPIO6` UART wiring is intact
- common ground is present

## Core Flow

1. Build and flash the GPIO interrupt loopback firmware over SWD.
2. Let the RP2040 emit a fixed burst of `100` pulses on `GPIO16`.
3. Count those pulses on `GPIO17` using rising-edge interrupts.
4. Report PASS only when the interrupt count matches the pulse target.
5. Capture the bounded PASS string through the S3JTAG Web UART bridge.

## Canonical Command

```bash
python3 -m ael run \
  --test tests/plans/rp2040_gpio_interrupt_loopback_with_s3jtag.json \
  --board rp2040_pico_s3jtag_uart
```

## Validated Result Shape

Expected UART evidence includes:
- `AEL_READY RP2040 GPIO_IRQ PASS`
- `count=100`
- `target=100`

## Recovery Rules

If the test fails before UART observe:
- recheck SWD reachability first

If the test reaches UART observe but reports FAIL or times out:
- recheck the local jumper first: `GPIO16 -> GPIO17`
- then recheck the UART wiring to `GPIO7/GPIO6`
- if UART itself is suspect, run `rp2040_uart_rxd_detect_with_s3jtag` before debugging the interrupt firmware

## Success Criteria

This skill has succeeded when:
- the firmware is flashed over SWD
- the DUT reports `AEL_READY RP2040 GPIO_IRQ PASS count=100 target=100`
- formal `rp2040_gpio_interrupt_loopback_with_s3jtag` reaches `PASS: Run verified`

## Why This Test Is Valuable

Compared with simple `TARGETIN` level/frequency tests, this one exercises real RP2040 peripheral behavior:
- GPIO output generation
- GPIO input sensing
- interrupt edge handling
- bounded DUT-side verification logic

That makes it a strong reusable `Stage 2` feature test for `RP2040 + S3JTAG`.
