# STM32F103RCT6

**MCU:** STM32F103RCT6 — Cortex-M3, 72 MHz max (8 MHz HSI default), 256 KB flash, 48 KB RAM, 64-pin LQFP
**Family:** STM32F1 (high density)
**Status:** verified
**Verification date:** 2026-03-17

---

## Verification Suite

Suite name: `smoke_stm32f103rct6`
Pack: `packs/smoke_stm32f103rct6.json`
Result: **7 / 7 PASS**

| # | Experiment | Test Plan | Loopback |
|---|-----------|-----------|---------|
| 1 | Mailbox basic | stm32f103rct6_mailbox | — |
| 2 | TIM2 interrupt | stm32f103rct6_timer_mailbox | — |
| 3 | GPIO loopback | stm32f103rct6_gpio_loopback | PB0 → PB1 |
| 4 | UART loopback | stm32f103rct6_uart_loopback | PA9 → PA10 |
| 5 | EXTI trigger | stm32f103rct6_exti_trigger | PB8 → PB9 |
| 6 | ADC loopback | stm32f103rct6_adc_loopback | PA0 → PA1 |
| 7 | SPI loopback | stm32f103rct6_spi_loopback | PB15 → PB14 |

---

## Bench Wiring

| DUT pin | Instrument (ESP32JTAG) | Role |
|---------|------------------------|------|
| SWDIO (PA13) / SWDCLK (PA14) | P3 | SWD debug / flash |
| GND | probe GND | Common ground |
| RESET | NC | Not connected |

Instrument: `esp32jtag_stm32_golden` @ 192.168.2.109, GDB port 4242.

## Board-side Loopbacks (per experiment)

| Short on DUT board | Used for |
|---|---|
| PB0 → PB1 | GPIO loopback |
| PA9 → PA10 | UART loopback |
| PB8 → PB9 | EXTI trigger |
| PA0 → PA1 | ADC loopback |
| PB15 → PB14 | SPI loopback |

---

## Flash / Probe Notes

- **BMP/BMDA (ESP32JTAG):** use `monitor swdp_scan` explicitly — `monitor a` does NOT trigger SWD scan for this target (detected as "STM32F1 VL density M3" by BMDA, which is a mis-identification but flash still works)
- **Mailbox verify:** must use `skip_attach: false` — BMDA `detach` fully disconnects, unlike ST-Link `disconnect`
- **Flash sequence:** `file {firmware}` → `monitor swdp_scan` → `attach 1` → `load` → `attach 1` → `detach`

## Known Issues

### Volatile NOP delay ~167x slower than expected

`delay()` and `DELAY_NOP()` volatile NOP loops run approximately 167x slower than calculated at 8 MHz HSI. Root cause unknown (clock config confirmed correct, DWT/VC bits ruled out). Hardware timers (TIM2) are unaffected.

**Workaround:** set `settle_s` generously in mailbox_verify:
- Tests without delay before PASS: 4–5 s
- Tests with delay() before PASS (gpio, exti, adc): 30–60 s

---

## Firmware

All firmware is bare-metal, 8 MHz HSI, no PLL.
Startup: `firmware/targets/stm32f103rct6/startup_stm32f103.c`
Linker script: `firmware/targets/stm32f103rct6/stm32f103rct6.ld`
Mailbox address: `0x2000BC00`
