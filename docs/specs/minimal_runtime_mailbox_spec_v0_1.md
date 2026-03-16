# Spec: Minimal Runtime Mailbox Baseline v0.1

## Status
Draft — concept validated on STM32G431CBU6 hardware (2026-03-16)

---

## Goal

Add a **baseline bring-up program** whose only job is to prove the most
fundamental truth about a board:

- firmware can be flashed over SWD
- MCU boots and reaches `main()`
- code can write structured status into RAM
- AEL can read that status back over the debug path

This is a **debug-path-only gate**, not a peripheral test. It must pass before
any other test is attempted.

---

## Motivation

The existing 8 bring-up programs validate peripheral features: GPIO waveform,
UART loopback, SPI, ADC, timer capture, EXTI, GPIO loopback, PWM.

All of them assume the following are already working:

- the board can be flashed and reset
- the MCU boots and runs code
- the SWD debug path is reliable
- the result reporting path works

None of them explicitly test those assumptions. If the board silently fails to
boot, or the mailbox is unreadable, every peripheral test will fail for the
same root cause — and there will be no targeted evidence pointing to it.

A minimal runtime baseline program makes that root cause testable in isolation.

**It should be the first program to run on any new board.**

---

## Scope

This spec defines the concept for any MCU board. The first implementation
target is STM32G431CBU6 (`stm32g431_minimal_runtime_mailbox`).

The same concept applies to any future board where:
- SWD or JTAG debug access is available
- RAM is writable by firmware
- `read_mailbox.py` or an equivalent tool can read target memory

---

## Dependencies

This program must depend **only** on:

| Dependency | Required |
|---|---|
| SWDIO / SWCLK | Yes |
| GND | Yes |
| Flash / debug access | Yes |
| RAM at `AEL_MAILBOX_ADDR` | Yes |
| GPIO result lines | No |
| External instrument (LA, ADC) | No |
| UART / SPI / ADC / EXTI / PWM | No |
| External loopback wiring | No |

If this program fails, the cause is in the flash/boot/debug path — not in
wiring, not in peripheral configuration.

---

## Mailbox Interface

Use the shared mailbox header `firmware/targets/ael_mailbox.h`:

```c
#include "../ael_mailbox.h"

/* Mailbox at 0x20007F00 (SRAM end - 256 bytes, STM32G431CBU6) */
/* Magic: 0xAE100001 */
/* Status: 0=empty, 1=running, 2=pass, 3=fail */
```

The `detail0` field carries a loop counter incremented each iteration, giving
evidence that the MCU is actively running (not just reset-looping):

```c
MAILBOX->detail0 = iteration_count;
```

This makes the mailbox content dynamic and distinguishable from a one-time
write followed by stall.

---

## Execution Model

```
power-on / reset
  └─ MCU boots from flash
       └─ reaches main()
            ├─ write magic = AEL_MAILBOX_MAGIC
            ├─ write status = STATUS_RUNNING      ← written last
            ├─ run minimal self-check
            │    (e.g. basic arithmetic, stack round-trip, constant check)
            ├─ on pass: write status = STATUS_PASS
            │           continue loop, increment detail0 each iteration
            └─ on fail: write error_code, write status = STATUS_FAIL
                        spin in tight loop (no detail0 update)
```

**Status is always written last** to prevent a partial write from being
misread as a complete result.

**After writing final status**, the program stays alive in a spinning loop so
AEL can attach and read the mailbox at any point without a timing race.

---

## What This Proves

| Claim | Evidence |
|---|---|
| Flash write succeeded | firmware executes at all |
| MCU boots from flash | `main()` is reached |
| RAM at mailbox address is writable | magic appears at `0x20007F00` |
| MCU is actively running | `detail0` counter increments on repeated reads |
| AEL debug read path works | `read_mailbox.py` returns structured result |
| Result is stable and repeatable | three consecutive reads return same status |

**This program does not prove:** GPIO physical behavior, peripheral correctness,
or external wiring. Those belong to the 8 peripheral tests that follow.

---

## Role in the Bring-Up Sequence

```
New board arrives
  └─ Step 0: minimal_runtime_mailbox
       └─ PASS → debug path confirmed, MCU alive
            └─ Step 1: wiring / observe-map verification
                 └─ Step 2..9: GPIO, UART, SPI, ADC, capture, EXTI, loopback, PWM
```

This program is:
- **operationally first** — must pass before any other test is attempted
- **logically independent** — does not share dependencies with the 8
  peripheral tests and does not block or replace them

A failure here surfaces a boot or debug path problem immediately, before time
is spent debugging peripheral firmware.

---

## Read Mechanism

After flashing and waiting for the board to settle (~3–5 seconds), read the
mailbox using the existing tool:

```bash
python3 tools/read_mailbox.py --ip 192.168.2.62
```

For repeated reads (to confirm `detail0` increments):

```bash
python3 tools/read_mailbox.py --ip 192.168.2.62
sleep 1
python3 tools/read_mailbox.py --ip 192.168.2.62
```

`detail0` should be larger on the second read if the MCU is running.

---

## Acceptance Criteria

### Pass

| Field | Expected value |
|---|---|
| `magic` | `0xAE100001` |
| `status` | `2` (STATUS_PASS) |
| `error_code` | `0x00000000` |
| `detail0` | non-zero; increases between reads |

### Fail cases and their meaning

| Symptom | Likely cause |
|---|---|
| GDB cannot attach | SWD wiring problem or board not powered |
| `magic` reads `0x00000000` or `0xFFFFFFFF` | MCU did not reach `main()` (boot failure, bad flash) |
| `magic` = correct, `status` = `1` (RUNNING) after 10s | Self-check is hanging |
| `magic` = correct, `status` = `3` (FAIL) | Self-check detected an error; inspect `error_code` |
| `detail0` does not change between reads | MCU halted or stuck after writing status |

---

## Implementation Reference

The STM32G431CBU6 PoC implementation is at:

```
firmware/targets/stm32g431_mailbox_poc/main.c
```

This implementation was validated on hardware on 2026-03-16:
- PASS variant: `magic=0xAE100001, status=2, error_code=0, detail0=0` ✓
- FAIL variant: `magic=0xAE100001, status=3, error_code=0xDEAD0001, detail0=0xCAFE` ✓

For production use, the PoC should be cleaned up and renamed to
`stm32g431_minimal_runtime_mailbox`.

---

## One-Sentence Summary

**The Minimal Runtime Mailbox Baseline is a debug-path-only program that proves
a board can be flashed, booted, and read over SWD before any peripheral or
wiring tests are attempted — acting as the mandatory first gate in any new
board bring-up sequence.**
