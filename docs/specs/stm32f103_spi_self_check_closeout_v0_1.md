# STM32F103 SPI Self-Check Closeout v0.1

## Path
- board: `stm32f103`
- fixture: `stm32f103_unified_capability_fixture_v0_1`
- firmware target: `firmware/targets/stm32f103_spi`
- test plan: `tests/plans/stm32f103_spi_banner.json`

## Wiring used
- external observe:
  - `PA4 -> P0.0`
  - optional auxiliary observe: `PA5 -> P0.1`
- preserved fixture loopbacks:
  - `PA1 -> PA0`
  - `PA9 -> PA10`
  - `PA8 -> PB8`
- SPI loopback:
  - `PA7 -> PA6`

## Bounded success method
- SPI uses:
  - `PA5 = SPI1_SCK`
  - `PA7 = SPI1_MOSI`
  - `PA6 = SPI1_MISO`
- firmware performs a bounded SPI loopback self-check internally
- firmware exports SPI pass/fail status on `PA4`
- AEL verifies `PA4` through the existing external observe path

## Live result
- run id: `2026-03-13_10-13-28_stm32f103_stm32f103_spi_banner`
- result: `PASS`
- verify summary:
  - `edges=25`
  - `high=32640`
  - `low=32892`
  - `window=0.252s`

## What this proves
- the unified STM32 capability fixture can support a bounded SPI self-check without new instrument roles
- `PA5/PA6/PA7` can be treated as SPI-internal wiring only
- `PA4` can continue to serve as the external machine-checkable proof signal
- the STM32F103 capability anchor now has bounded live-pass execution evidence for:
  - GPIO
  - UART
  - ADC
  - SPI

## What this does not prove
- unrestricted repeat-pass stability for the SPI path
- general SPI protocol analysis support
- direct external proof on `PA5/PA6/PA7`

## Repeat note
- a follow-on 3-run repeat attempt was not accepted as bench evidence because all three reruns failed in preflight under restricted execution context (`Operation not permitted`)
- therefore this path is recorded as `live-pass`, not `repeat-pass`

## Recommended next path
- `PA8 -> PB8` bounded digital timing path
  - PWM
  - GPIO self-check
  - EXTI
  - capture/timing-class demos
