# RP2040 S3JTAG PWM Validation Skill

## Purpose

Capture the reusable workflow for validating `RP2040` hardware PWM through the `S3JTAG` bench using `TARGETIN` as the measurement path.

This skill is useful because it avoids the Web UART bridge entirely for pass/fail, which makes it a strong `Stage 2` peripheral test after SWD is already known-good.

## Trigger / When To Use

Use this skill when:
- the instrument is `S3JTAG`
- the target is flashed over `192.168.4.1:4242`
- a target PWM output can be wired into `TARGETIN`
- you want a `Stage 2` peripheral test that does not depend on UART observe stability

## Validated Scope

Validated bench shape:
- `S3JTAG SWCLK GPIO4` -> target `SWCLK`
- `S3JTAG SWDIO GPIO5` -> target `SWDIO`
- target `GPIO18/PWM_OUT` -> `S3JTAG TARGETIN GPIO15`
- common ground

Validated target on 2026-03-26:
- `RP2040 Pico`
- PWM output pin: `GPIO18`
- expected waveform: approximately `1 kHz`, `50%` duty
- validated formal test: `tests/plans/rp2040_pwm_capture_with_s3jtag.json`
- validated successful run id: `2026-03-26_21-25-33_rp2040_pico_s3jtag_rp2040_pwm_capture_with_s3jtag`

## Preconditions

Required host and bench assumptions:
- host is joined to `esp32jtag_0F91`
- `192.168.4.1:4242` is reachable
- SWD wiring is intact
- `GPIO18/PWM_OUT` is wired to `TARGETIN(GPIO15)`
- common ground is present

## Core Flow

1. Confirm the host is on the AP and `monitor swd_scan` still finds the RP2040.
2. Build and flash the PWM firmware over SWD.
3. Let AEL validate the signal through `TARGETIN` using frequency and duty bounds.
4. Treat `estimated_hz` and duty window as the primary evidence.

## Canonical Commands

Confirm SWD health:

```bash
arm-none-eabi-gdb -q \
  -ex 'target extended-remote 192.168.4.1:4242' \
  -ex 'monitor swd_scan' \
  -ex 'quit'
```

Run the formal test:

```bash
python3 -m ael run \
  --test tests/plans/rp2040_pwm_capture_with_s3jtag.json \
  --board rp2040_pico_s3jtag
```

## Validated Result Shape

Expected verify evidence includes:
- `state=toggle`
- `estimated_hz` close to `1000`
- duty within approximately `0.45` to `0.55`

Validated live result:
- `estimated_hz=995`

## Recovery Rules

If `preflight` fails before build:
- check AP association first
- restore `esp32jtag_0F91` connectivity before blaming PWM logic

If signal verify fails:
- first recheck the single added wire: `GPIO18 -> TARGETIN`
- then inspect PWM frequency/duty parameters in firmware

## Success Criteria

This skill has succeeded when:
- the PWM firmware is flashed over SWD
- `TARGETIN` sees a stable toggle
- frequency lands near `1 kHz`
- duty lands near `50%`
- formal `rp2040_pwm_capture_with_s3jtag` reaches `PASS: Run verified`

## Why This Test Is Valuable

Compared with UART-backed peripheral tests, this one is simpler to trust:
- no Web UART dependency
- no pattern-matching on console text
- direct signal measurement at the instrument input

That makes it a strong reusable `Stage 2` peripheral validation for `RP2040 + S3JTAG`.
