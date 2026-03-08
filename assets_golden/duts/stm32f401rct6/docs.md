# stm32f401rct6

Wiring expectations:
- SWD via ESP32JTAG P3
- PA4..PA7 -> LA CH1..CH4 (P0.0..P0.3)
- LED on PC13

Notes:
- Introduced from the older `stm32f103` GPIO-signature path.
- Uses repo-root firmware project at `firmware/targets/stm32f401rct6`.
- The STM32F103 path is intentionally left for later cleanup and should not be treated as a fresh gold-standard reference.
