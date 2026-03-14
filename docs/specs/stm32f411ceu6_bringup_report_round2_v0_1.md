# STM32F411CEU6 Bring-Up Report Round 2 v0.1

## Identity

- MCU: `stm32f411ceu6`
- board/module: `STM32F411CEU6 WeAct Black Pill V2.0`
- DUT instance or bench target: `stm32f411ceu6`
- report date: `2026-03-14`
- author: `Codex`

## Scope of this round

- goal of this bring-up round:
  - extend the validated GPIO baseline into the first F411 self-check suite
  - validate UART loopback, ADC loopback, GPIO loopback, PWM, EXTI, and capture on real hardware
  - identify the remaining SPI-specific blocker
- out of scope:
  - UART bridge / host-serial banner path
  - I2C

## Confirmed bench contract used

- control instrument:
  - `esp32jtag_stm32f411 @ 192.168.2.103:4242`
- fixed wiring:
  - `SWD -> P3`
  - `RESET -> NC`
  - `GND -> probe GND`
  - `PA2 -> P0.0`
  - `PA3 -> P0.1`
  - `PB13 -> P0.2`
  - `PC13 -> LED`
- jumpers:
  - ADC: `PB1 -> PB0`
  - shared loopback: `PA8 -> PA6`
  - UART loopback: `PA9 -> PA10`
  - SPI loopback: `PB15 -> PB14`

## Official implementation basis

- STM32 device header and startup:
  - `firmware/targets/stm32f411ceu6/vendor/include/st/stm32f411xe.h`
  - `firmware/targets/stm32f411ceu6/vendor/st/system_stm32f4xx.c`
  - `firmware/targets/stm32f411ceu6/vendor/st/startup_stm32f411xe.s`
- official family/example anchoring used for peripheral choices:
  - `USART1` on `PA9/PA10`
  - `ADC1_IN8` on `PB0`
  - `SPI2` on `PB13/PB14/PB15`
  - `TIM1_CH1` on `PA8`
  - `TIM3_CH1` on `PA6`

## AEL methodology basis

- reused from validated STM32F103 patterns:
  - bounded proof-pin export for self-check tests
  - manual loopback contract recorded in plan `bench_setup`
  - operator-visible LED heartbeat
  - plan naming and signal-verification structure
- intentionally not reused:
  - STM32F103 register layout
  - STM32F103 pin mappings

## Tests attempted

| test | result | run id | notes |
| --- | --- | --- | --- |
| `stm32f411_uart_loopback_banner` | pass | `2026-03-14_07-26-45_stm32f411ceu6_stm32f411_uart_loopback_banner` | `PA9 -> PA10` loopback succeeded on live hardware. |
| `stm32f411_adc_banner` | pass | `2026-03-14_07-27-26_stm32f411ceu6_stm32f411_adc_banner` | `PB1 -> PB0` ADC loopback succeeded on live hardware. |
| `stm32f411_gpio_loopback_banner` | pass | `2026-03-14_07-27-47_stm32f411ceu6_stm32f411_gpio_loopback_banner` | `PA8 -> PA6` GPIO loopback succeeded on live hardware. |
| `stm32f411_pwm_banner` | pass | `2026-03-14_07-28-10_stm32f411ceu6_stm32f411_pwm_banner` | `PA8 -> PA6` PWM self-check succeeded on live hardware. |
| `stm32f411_exti_banner` | pass | `2026-03-14_07-28-33_stm32f411ceu6_stm32f411_exti_banner` | `PA8 -> PA6` EXTI self-check succeeded on live hardware. |
| `stm32f411_capture_banner` | pass | `2026-03-14_07-28-54_stm32f411ceu6_stm32f411_capture_banner` | `PA8 -> PA6` capture self-check succeeded on live hardware. |
| `stm32f411_spi_banner` | fail | `2026-03-14_07-16-29_stm32f411ceu6_stm32f411_spi_banner` | build/flash succeeded, but `PA2` proof stayed low and a temporary direct probe of `PB13` also saw no SCK activity on `P0.2`. |

## Result classification

- passed:
  - `stm32f411_uart_loopback_banner`
  - `stm32f411_adc_banner`
  - `stm32f411_gpio_loopback_banner`
  - `stm32f411_pwm_banner`
  - `stm32f411_exti_banner`
  - `stm32f411_capture_banner`
- failed:
  - `stm32f411_spi_banner`
- partial:
  - F411 self-check proof signals were initially measured near `24 Hz`, not the F103-like `50 Hz` window used in the first draft plans
- blocked:
  - none; the SPI issue is a real test failure, not a bench-unreachable block

## Inferred assumptions

- inference:
  - the current F411 self-check proof signal is stable near `24 Hz`
  - why it was inferred:
    - repeated live captures for UART, ADC, GPIO loopback, PWM, EXTI, and capture all produced about `12` edges over a `0.252 s` window
  - confidence:
    - high
  - action taken:
    - retuned F411 self-check plan windows from `35..70 Hz` to `15..35 Hz`

## Rejected paths

- rejected path:
  - forcing F411 proof windows to match STM32F103 without measurement
  - why it was rejected:
    - live captures showed the F411 proof cadence is different even though the methodology is the same
- rejected path:
  - treating the SPI failure as another proof-window issue
  - why it was rejected:
    - `PB13` direct probing also showed no observed SPI clock activity

## Lessons learned

- what succeeded:
  - the staged methodology transfer from STM32F103 works well on F411 when the implementation is rebuilt from official F411 headers/startup
  - one fixed proof-pin strategy on `PA2` works for the F411 self-check family
- what failed:
  - the first draft proof windows assumed F103-like proof frequency and caused false verify failures
  - SPI2 on `PB13/PB14/PB15` is not yet producing observable SCK activity on this bench/board state
- what was learned:
  - methodology reuse is portable; proof timing is not
  - F411 plans should record the measured proof range rather than inherit F103 thresholds
  - the remaining SPI issue is specifically in the SPI path, not in the generic F411 board setup

## Recommended next step

- next safest implementation step:
  - isolate the F411 SPI path by checking whether `PB13 -> P0.2` can be driven directly as GPIO on this board/bench, then verify the SPI2 pin mux/runtime behavior from there
- next safest validation step:
  - rerun `stm32f411_spi_banner` after the SPI2/PB13 observation issue is resolved
- current overall status:
  - F411 bring-up is materially established with `7/8` first-pass tests implemented and `6/7` new peripheral/self-check tests passing, plus the previously validated GPIO signature baseline
