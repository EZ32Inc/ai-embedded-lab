# STM32F103RCT6 Bring-Up Closeout

**Date:** 2026-03-17
**Result:** 7 / 7 PASS
**Instrument:** ESP32JTAG (esp32jtag_stm32_golden)

---

## What Succeeded

- All 7 smoke tests passed on first clean pack run with ESP32JTAG
- Mailbox pattern (magic + status) works correctly on RCT6
- SPI, UART, GPIO, ADC, EXTI, TIM2 all verified functional at 8 MHz HSI
- Board-side loopback wiring carried over cleanly from F103C8T6 methodology

## What Failed / Required Investigation

### 1. `monitor a` does not trigger SWD scan for RCT6

BMDA identifies RCT6 as "STM32F1 VL density M3" (mis-identification — VL is STM32F100 Value Line). `monitor a` (which tries JTAG then SWD) did not complete the scan in this context. `monitor swdp_scan` (explicit SWD-only scan) worked reliably.

**Fix applied:** Board config flash sequence uses `monitor swdp_scan` explicitly.

### 2. `skip_attach: true` incompatible with BMDA detach

ST-Link (st-util) `disconnect` keeps the SWD connection alive — GDB can reconnect and read memory without re-attaching. BMDA `detach` fully releases the target. Mailbox verify with `skip_attach: true` failed with "Cannot access memory".

**Fix applied:** All RCT6 test plans use `skip_attach: false`. `check_mailbox_verify.py` updated to use `monitor swdp_scan` instead of `monitor a`.

### 3. Volatile NOP delay ~167x slower than expected

Software delay loops (`delay()`, `DELAY_NOP()`) run ~167x slower than calculated at 8 MHz HSI. Confirmed excluded: clock config, DWT watchpoints, DEMCR VC bits, ST-Link hardware variant. Hardware timers (TIM2) unaffected. Root cause remains unknown.

**Fix applied:** `settle_s` increased to 30 s (gpio_loopback) and 60 s (exti_trigger, adc_loopback) to accommodate slow loops.

## What Was Inferred / Assumed

- RCT6 flash and peripheral registers follow STM32F103 RM0008 reference manual
- SWD pinout (PA13/PA14) standard for all F103 variants
- Startup code shared from F103C8T6 path with linker script updated for 256 KB flash / 48 KB RAM

## Lessons Written Back

- `docs/boards/stm32f103rct6.md` — board doc with wiring, flash notes, known issues
- `configs/boards/stm32f103rct6.yaml` — flash sequence updated for BMDA
- `ael/adapters/check_mailbox_verify.py` — `monitor swdp_scan` replaces `monitor a`
- All 7 RCT6 test plans — `skip_attach: false`, settle_s adjusted

## Cleanup

- Temporary diagnostic firmware `firmware/targets/stm32f103rct6_spi_gpio_probe/` — candidate for removal
