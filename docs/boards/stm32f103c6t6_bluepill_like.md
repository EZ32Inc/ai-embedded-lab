# STM32F103C6T6 Bluepill-like

**MCU:** STM32F103C6T6 — Cortex-M3, 72 MHz max (8 MHz HSI default), 32 KB flash, 10 KB RAM, 48-pin LQFP
**Family:** STM32F1
**Status:** minimal visual baseline verified
**Verification date:** 2026-03-28

---

## Minimal Baseline

Suite name: `smoke_stm32f103c6_minimal`
Pack: `packs/smoke_stm32f103c6_minimal.json`
Result: **1 / 1 PASS** on a known-good physical board

| # | Experiment | Test Plan | Verification |
|---|-----------|-----------|--------------|
| 1 | PC13 blinky visual | stm32f103c6_pc13_blinky_visual | operator-visible LED blink |

---

## Bench Wiring

| DUT pin | Instrument (ESP32JTAG) | Role |
|---------|------------------------|------|
| SWDIO / SWDCLK | P3 | SWD debug / flash |
| PC13 | LED | Onboard status LED |
| GND | probe GND | Common ground |
| RESET | NC | Not connected |

Instrument: `esp32jtag_blackpill_192_168_2_106` @ `192.168.2.106`, GDB port `4242`.

---

## Firmware Baseline

Current accepted minimal firmware:

- reference-style `PC13` blinky
- `BSRR` set/reset writes
- active-low LED assumption matching common Bluepill behavior
- no mailbox logic
- no unrelated GPIO activity

Implementation:

- [main.c](/nvme1t/work/codex/ai-embedded-lab/firmware/targets/stm32f103c6_gpio_no_external_capture/main.c)

Accepted baseline commit:

- `a515dd2` `Use reference-style STM32F103C6 PC13 blinky`

---

## Notes

- Same-type low-cost boards were not interchangeable during bring-up; at least one board behaved correctly only after switching to another physical unit.
- Treat this page as the first minimal known-good anchor, not yet a full board qualification.
- Normal run setting for flash execution is `BOOT0=0`, `BOOT1=0`.

---

## Next Steps

This board path is intentionally incomplete today.

Current status:

- minimal visual `PC13` blinky is validated
- this is the first known-good baseline only
- this is not yet a complete board suite

Planned follow-up:

- add additional independent tests beyond visual blinky
- build toward a fuller `STM32F103C6T6` suite
- prefer machine-checkable tests after the visual baseline
- keep using the known-good board first when expanding the suite

Recommended sequencing:

1. keep the current `PC13` blinky as the minimal board-health anchor
2. add one simple machine-verifiable GPIO proof test
3. add a small staged smoke suite
4. expand later toward a more complete board capability set
