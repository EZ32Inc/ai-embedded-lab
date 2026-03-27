# RP2040 S3JTAG SPI Validation Skill

## Purpose

Capture the reusable workflow for validating `RP2040 SPI0` loopback through the `S3JTAG` bench when the target is flashed over SWD and the SPI pass/fail result is reported through the ESP32-S3 internal Web UART bridge.

This skill exists because the first visible SPI failures were not caused by the SPI datapath itself. They were blocked by the shared UART observation path.

## Trigger / When To Use

Use this skill when:
- the instrument is `S3JTAG` or another generic `esp32s3_devkit`-class probe
- the target is flashed over `192.168.4.1:4242`
- the SPI test reports results through the ESP32-S3 internal Web UART path
- a new SPI test appears to fail at `check_uart` rather than at build or flash
- you need to separate true SPI mismatches from upstream UART observation instability

## Validated Scope

Validated bench shape:
- `S3JTAG SWCLK GPIO4` -> target `SWCLK`
- `S3JTAG SWDIO GPIO5` -> target `SWDIO`
- target `UART TX` -> `S3JTAG UART1 RX GPIO7`
- target `UART RX` -> `S3JTAG UART1 TX GPIO6`
- target `SPI0 TX GPIO3` -> target `SPI0 RX GPIO4`
- common ground

Validated target on 2026-03-26:
- `RP2040 Pico`
- target UART: `UART0` on `GPIO0/GPIO1`
- target SPI: `SPI0`
- `SPI0_SCK` on `GPIO2`
- `SPI0_TX` on `GPIO3`
- `SPI0_RX` on `GPIO4`
- pattern under test: `55 AA 3C C3`
- validated formal test: `tests/plans/rp2040_spi_loopback_with_s3jtag.json`
- validated successful run id: `2026-03-26_21-13-25_rp2040_pico_s3jtag_uart_rp2040_spi_loopback_with_s3jtag`

## Preconditions

Required host and bench assumptions:
- host is joined to `esp32jtag_0F91`
- instrument web API is reachable at `https://192.168.4.1`
- BMP/GDB remote is reachable at `192.168.4.1:4242`
- RP2040 SWD wiring is intact
- RP2040 `GPIO0/UART0_TX` is wired to `GPIO7`
- RP2040 `GPIO1/UART0_RX` is wired to `GPIO6`
- RP2040 `GPIO3/SPI0_TX` is jumpered to `GPIO4/SPI0_RX`

Required firmware state:
- ESP32-S3 devkit UART image is flashed
- AP defaults are `esp32jtag` / `esp32jtag`
- UART banner test is already passing reliably on the same bench state

## Core Rule

Do not debug SPI first if the SPI test reports through Web UART and `UART banner` is not currently stable.

The reusable dependency order is:
1. SWD/GDB health
2. Web UART health
3. SPI loopback functional result

If step 2 is not stable, a SPI test can fail at `check_uart` even when the SPI loopback itself is fine.

## Core Flow

1. Confirm the host is on the S3 AP and `monitor swd_scan` still finds the RP2040.
2. Confirm `rp2040_uart_banner_with_s3jtag` passes on the current bench state.
3. Build and flash the SPI loopback firmware over SWD.
4. Observe SPI progress and result through Web UART.
5. Treat only `SPI PASS` or `SPI FAIL expect=... got=...` as SPI datapath evidence.
6. If the run fails at `check_uart`, go back and stabilize UART first.

## Validated Firmware Behavior

The SPI loopback firmware emits staged UART messages:
- `AEL_READY RP2040 SPI BOOT`
- `AEL_READY RP2040 SPI WAIT`
- `AEL_READY RP2040 SPI XFER`
- `AEL_READY RP2040 SPI PASS rx=... count=...`
- `AEL_READY RP2040 SPI FAIL expect=... got=...`

This means the UART stream can be used to localize failure stage quickly:
- only `BOOT/WAIT` seen: loop did not reach transfer yet
- `XFER` then `FAIL`: SPI datapath mismatch
- `PASS`: SPI loopback good
- no UART text at all: diagnose UART path before blaming SPI

## Canonical Commands

Confirm SWD health:

```bash
arm-none-eabi-gdb -q \
  -ex 'target extended-remote 192.168.4.1:4242' \
  -ex 'monitor swd_scan' \
  -ex 'quit'
```

Run UART baseline first:

```bash
python3 -m ael run \
  --test tests/plans/rp2040_uart_banner_with_s3jtag.json \
  --board rp2040_pico_s3jtag_uart
```

Run SPI loopback:

```bash
python3 -m ael run \
  --test tests/plans/rp2040_spi_loopback_with_s3jtag.json \
  --board rp2040_pico_s3jtag_uart
```

## Recovery Rules

If `192.168.4.1:4242` is down:
- restore AP connectivity first
- confirm `monitor swd_scan` before touching SPI logic

If `UART banner` is failing:
- stop treating SPI `check_uart` failures as SPI evidence
- re-establish UART health first

If SPI still fails after UART is stable:
- inspect the staged SPI UART messages
- look specifically for `SPI FAIL expect=... got=...`
- only then adjust SPI wiring, rate, or firmware logic

## Success Criteria

This skill has succeeded when:
- `UART banner` is already passing on the same bench
- the SPI loopback firmware is flashed over SWD
- formal `rp2040_spi_loopback_with_s3jtag` reaches `PASS: Run verified`
- the run artifacts show `key_checks_passed=uart.verify`
- the validated loopback contract remains `GPIO3 -> GPIO4`

## Why This Was Easy To Miss

The first visible symptom for this SPI test was not a SPI mismatch string. It was the same `check_uart` failure shape already seen in the UART workflow.

The better rule is:
- when a peripheral test reports through Web UART, stabilize the reporting channel before debugging the peripheral itself

That prevents wasting time on SPI firmware or wiring when the real blocker is upstream observation.
