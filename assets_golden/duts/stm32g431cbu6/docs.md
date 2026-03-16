# stm32g431cbu6

STM32G431CBU6 — QFP48 (LQFP48), 128KB flash, 32KB RAM, Cortex-M4 @ 170MHz max (16MHz HSI default).
WeAct STM32G431CxTx CoreBoard V1.0.

Schematic reference: WeAct-STM32G431CxTxCoreBoard_V10_SchDoc.pdf (QFP48 variant)

## Key Architecture Difference vs STM32F4

| Feature | STM32G4 | STM32F4 |
|---------|---------|---------|
| GPIO bus | AHB2 (0x48000000) | AHB1 (0x40020000) |
| RCC AHB enable reg | AHB2ENR at RCC+0x4C | AHB1ENR at RCC+0x30 |
| GPIOA base | 0x48000000 | 0x40020000 |

Do NOT copy F4 register addresses into G4 firmware — bus is different.

## Onboard Components

| Pin | Function | Notes |
|-----|----------|-------|
| PA8 | User LED | Active-high |
| PB8 | BOOT0 button | Hold during reset for DFU |
| PA2 | UART2 TX | Also usable as GPIO |
| PA3 | UART2 RX | Also usable as GPIO |
| PC14/PC15 | HSE 8MHz oscillator | Not available as GPIO |

Note: PC13 is NOT present / NOT connected on this board.

## Bench Wiring

### Instrument connections (5)

| DUT pin | Instrument (ESP32JTAG) | Role |
|---------|------------------------|------|
| PA2     | P0.0                   | Primary signal / banner result |
| PA3     | P0.1                   | Secondary signal (half-rate) |
| PB3     | P0.2                   | SPI1 SCK observation |
| PA8     | LED                    | Operator-visible heartbeat LED |
| GND     | probe GND              | Common ground |
| SWDIO/SWDCLK | P3            | Debug / flash (SWD) |

### DUT loopback wires (4, board-side only)

| Short | Purpose |
|-------|---------|
| PA9 ↔ PA10 | USART1 TX→RX |
| PB5 ↔ PB4  | SPI1 MOSI→MISO |
| PB1 ↔ PB0  | ADC source→input |
| PA8 ↔ PA6  | Capture / EXTI / GPIO / PWM output→input |

All wires connected once at session start. No mid-suite rewiring required.

## Instrument

`esp32jtag_stm32_golden` at `192.168.2.98`, GDB port 4242.

## Firmware

Bare-metal, no CMSIS dependency. Custom startup.c to avoid `_sidata` linker issue.
- Clock: 16MHz HSI (no PLL configured)
- SysTick: RVR=15999 → 1kHz tick from 16MHz HSI
- PA2: toggles every tick → ~250Hz square wave
- PA3: toggles every 2 ticks → ~125Hz (ratio 2:1)
- PA8: toggles every 500 ticks → 1Hz LED blink (active-high)

Source: `firmware/targets/stm32g431cbu6/`

## Notes

- G4 series GPIO is on AHB2, not AHB1 — critical for bare-metal register access.
- RCC AHB2ENR: GPIOAEN = bit 0. Only GPIOA clock needed (PA2/PA3/PA8 all on GPIOA).
- Custom startup.c copies .data from `_etext` (no CMSIS `_sidata` symbol needed).
- HSE 8MHz available if PLL needed in future experiments.
