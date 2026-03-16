# Banner Experiment Pattern Skill

## Purpose

Explain and guide the implementation of the "banner experiment" firmware
architecture used across AEL's STM32F4 (and compatible) experiment suites.

---

## Trigger

Use this skill whenever:

- Designing a new peripheral self-test experiment for a verified board
- Explaining why an experiment only monitors PA2 despite testing SPI/UART/ADC/etc.
- Porting a banner experiment to a new MCU variant
- Debugging a banner experiment that reports unexpected PASS or FAIL

---

## What Is the Banner Pattern?

A banner experiment is a firmware architecture where:

1. **The MCU runs the peripheral test internally** — it exercises the peripheral
   (e.g. sends/receives over SPI, measures ADC, counts EXTI edges)
2. **The MCU self-evaluates the result** — it compares actual vs expected outcome
3. **The MCU broadcasts the result on a single GPIO** — PA2 drives a continuous
   square wave to signal PASS; a different pattern (or no signal) signals FAIL
4. **The instrument only watches PA2** — it does not need to understand the
   peripheral protocol; it only checks whether PA2 is toggling correctly

```
┌─────────────────────────────────┐
│  MCU Firmware                   │
│                                 │
│  1. Run peripheral test         │
│     (SPI loopback, ADC read...) │
│                                 │
│  2. Compare result vs expected  │
│                                 │
│  3. if PASS: toggle PA2 @ Fpass │◄──── instrument captures PA2
│     if FAIL: PA2 stays low      │      checks freq / edges
└─────────────────────────────────┘
```

---

## Why This Architecture?

| Property | Benefit |
|----------|---------|
| Single observation point (PA2) | Instrument doesn't need protocol-specific logic |
| Self-contained test logic | Firmware validates its own peripheral, no host-side orchestration |
| Binary result encoding | PASS/FAIL is unambiguous from a frequency check |
| Reusable infrastructure | Same test plan template works for UART, SPI, ADC, TIM, EXTI |

---

## Standard Signal Convention (STM32F4 suite)

| Signal | Role |
|--------|------|
| PA2 | Primary result output — toggles at ~250Hz on PASS |
| PA3 | Secondary signature — toggles at ~125Hz (half of PA2), ratio check |
| PC13 | Heartbeat LED — 500ms blink, operator-visible only |

The instrument verifies:
- PA2 frequency in range (e.g. 150–400 Hz)
- PA3 frequency in range (e.g. 75–200 Hz)
- PA2/PA3 ratio ≈ 2.0 (1.8–2.2)

---

## Firmware Template

```c
int main(void) {
    // 1. Init clocks, GPIO, peripheral under test
    rcc_init();
    gpio_init();
    peripheral_init();   // UART / SPI / ADC / TIM / EXTI

    // 2. Run self-test
    int result = run_self_test();   // returns 1=PASS, 0=FAIL

    // 3. Report result on PA2/PA3
    if (result) {
        // PASS: toggle PA2 @ ~250Hz, PA3 @ ~125Hz via SysTick
        systick_start();
        while (1) { toggle_outputs_on_tick(); }
    } else {
        // FAIL: PA2 stays low (or blinks error pattern)
        while (1) {}
    }
}
```

---

## Porting to a New MCU

When porting a banner experiment from F411 to F401 (or any new F4 variant):

1. Change `#include "stm32f411xe.h"` → `#include "stm32f401xc.h"` (or target header)
2. Verify peripheral register addresses are the same (F401/F411 are identical)
3. Check linker script symbols (see `cmsis_startup_symbol_skill.md`)
4. Keep PA2/PA3 output logic unchanged — it is the result reporting layer

---

## Checklist for a New Banner Experiment

- [ ] Peripheral init code is self-contained (no host commands needed)
- [ ] Self-test has a clear pass/fail criterion
- [ ] PA2 toggles continuously on PASS (not just once)
- [ ] PA3 toggles at exactly half the rate of PA2
- [ ] Test plan `signal_checks` thresholds set from measured values (see `gpio_signal_threshold_skill.md`)
- [ ] Test plan has `signal_relations` ratio check (PA2/PA3 ≈ 2.0)
- [ ] `bench_setup.peripheral_signals` lists all required DUT pins
