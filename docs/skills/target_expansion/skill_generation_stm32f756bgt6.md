# STM32F756BGT6 GPIO Golden Target Generation

Template basis:
- board config: `configs/boards/stm32f401rct6.yaml`
- firmware shape: `firmware/targets/stm32f401rct6`

Chosen provisional pattern:
- probe/instrument: `esp32jtag_stm32_golden`
- primary verify signal: `PA4 -> P0.0`
- auxiliary signals: `PA3 -> P0.1`, `PA2 -> P0.2`
- provisional LED: `PC13 -> P0.3` and `PC13 -> LED`

Firmware assumptions:
- family modeled as STM32F7-style GPIO/RCC, close to F4 register layout for this minimal use
- default core clock assumed `16 MHz HSI`
- minimal bring-up only; no cache or PLL setup

What to confirm on real hardware:
- package really exposes `PA2`, `PA3`, `PA4`, `PC13`
- board LED, if any, is actually on `PC13`
- target flash/RAM sizes match the linker script
- SWD wiring on bench slot matches `P3`

Plan-stage only intent:
- use `gpio_signature.json`
- validate with `inventory describe-test`, `describe-connection`, and `explain-stage --stage plan`
- do not treat this file as proof of flash/runtime correctness until hardware verify is done
