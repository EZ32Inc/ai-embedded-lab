# RP2040 S3JTAG Internal Temperature Validation Skill

## Purpose

Capture the reusable workflow for validating the RP2040 internal temperature sensor through the `S3JTAG` bench using only SWD and mailbox verification.

This skill is useful because it provides a real `Stage 1` no-wire self-test that does not depend on UART or TARGETIN.

## Trigger / When To Use

Use this skill when:
- the instrument is `S3JTAG`
- the target is flashed over `192.168.4.1:4242`
- you want a `Stage 1` no-wire self-test after the runtime gate
- you want to validate an internal RP2040 peripheral path without adding bench wiring

## Validated Scope

Validated bench shape:
- `S3JTAG SWCLK GPIO4` -> target `SWCLK`
- `S3JTAG SWDIO GPIO5` -> target `SWDIO`
- common ground

Validated target on 2026-03-26:
- `RP2040 Pico`
- formal test: `tests/plans/rp2040_internal_temp_mailbox_s3jtag.json`
- validated successful run id: `2026-03-26_21-56-53_rp2040_pico_s3jtag_rp2040_internal_temp_mailbox_s3jtag`

## Preconditions

Required host and bench assumptions:
- host is joined to `esp32jtag_0F91`
- `192.168.4.1:4242` is reachable
- SWD wiring is intact
- common ground is present

## Core Flow

1. Build and flash the internal temperature mailbox firmware over SWD.
2. Enable the RP2040 internal temperature sensor ADC path.
3. Take a bounded set of ADC samples on `ADC4`.
4. Check simple validity conditions on average and spread.
5. Report PASS/FAIL through the mailbox at `0x20041F00`.

## Canonical Command

```bash
python3 -m ael run \
  --test tests/plans/rp2040_internal_temp_mailbox_s3jtag.json \
  --board rp2040_pico_s3jtag
```

## Validated Result Shape

Expected success shape:
- build and flash succeed over SWD
- mailbox verify succeeds at `0x20041F00`
- run reaches `PASS: Run verified`

## Recovery Rules

If the test fails at preflight or flash:
- treat it as SWD/bench health first, not an ADC problem

If mailbox verify fails:
- inspect the firmware-side bounded checks first:
  - average sample `!= 0`
  - average sample `< 4095`
  - spread `> 0`
- use mailbox `detail0` as the first debug artifact because it carries average and spread without needing UART

## Success Criteria

This skill has succeeded when:
- the firmware is flashed over SWD
- mailbox verify passes
- formal `rp2040_internal_temp_mailbox_s3jtag` reaches `PASS: Run verified`

## Why This Test Is Valuable

Compared with Stage 2 wired tests, this one is cleaner and cheaper to run:
- no UART dependency
- no TARGETIN dependency
- no extra jumpers
- validates a real internal peripheral path

That makes it a strong reusable `Stage 1` no-wire self-test for `RP2040 + S3JTAG`.
