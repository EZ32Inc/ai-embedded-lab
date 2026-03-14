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
| `stm32f411_spi_banner` | fail | `2026-03-14_07-16-29_stm32f411ceu6_stm32f411_spi_banner` | Initial SPI attempt. Build/flash succeeded, but `PA2` proof stayed low before the later bench-solder fix and plan retuning. |
| `zz_tmp_stm32f411_spi_pa3_diag` | pass | `2026-03-14_08-22-42_stm32f411ceu6_zz_tmp_stm32f411_spi_pa3_diag` | Temporary diagnostic. `PA3 -> P0.1` toggled at about `24 Hz`, proving the firmware reaches the SPI transfer path and returns from `spi2_transfer()`. |
| `zz_tmp_stm32f411_spi_clock_probe` | pass | `2026-03-14_09-13-56_stm32f411ceu6_zz_tmp_stm32f411_spi_clock_probe` | Temporary diagnostic after solder repair. Continuous SPI2 traffic produced strong activity on `PB13 -> P0.2`, proving external SCK is visible. |
| `zz_tmp_stm32f411_pb13_gpio_probe` | pass | `2026-03-14_09-13-13_stm32f411ceu6_zz_tmp_stm32f411_pb13_gpio_probe` | Temporary diagnostic after solder repair. Direct GPIO toggling of `PB13` was visible on `P0.2`, proving the bench path is good. |
| `stm32f411_spi_banner` | pass | `2026-03-14_09-15-31_stm32f411ceu6_stm32f411_spi_banner` | Passed after fixing the `PB13/PB14` solder path and retuning the SPI proof window to the measured F411 range. |

## Result classification

- passed:
  - `stm32f411_uart_loopback_banner`
  - `stm32f411_adc_banner`
  - `stm32f411_gpio_loopback_banner`
  - `stm32f411_pwm_banner`
  - `stm32f411_exti_banner`
  - `stm32f411_capture_banner`
  - `stm32f411_spi_banner`
- resolved during round:
  - initial SPI failure on `stm32f411_spi_banner`
  - initial lack of visible `PB13 -> P0.2`
- partial:
  - F411 self-check proof signals were initially measured near `24 Hz`, not the F103-like `50 Hz` window used in the first draft plans
- blocked:
  - none

## Inferred assumptions

- inference:
  - the current F411 self-check proof signal is stable near `24 Hz`
  - why it was inferred:
    - repeated live captures for UART, ADC, GPIO loopback, PWM, EXTI, and capture all produced about `12` edges over a `0.252 s` window
  - confidence:
    - high
  - action taken:
    - retuned F411 self-check plan windows from `35..70 Hz` to `15..35 Hz`
- inference:
  - the SPI firmware control flow progresses past transfer launch and return
  - why it was inferred:
    - the temporary `PA3 -> P0.1` diagnostic toggled repeatedly during the SPI diagnostic run
  - confidence:
    - medium
  - action taken:
    - stopped treating the SPI issue as a total firmware dead path
- inference:
  - the initial SPI failure was caused by a real board interconnect issue on the `PB13/PB14` path, not by a fundamental F411 SPI implementation defect
  - why it was inferred:
    - after the solder repair, direct `PB13` GPIO probing and continuous SPI clock probing both passed, and the real SPI banner then passed after proof-window retuning
  - confidence:
    - high
  - action taken:
    - kept the implementation, repaired the physical connection, and aligned the SPI proof window to the measured F411 cadence

## Rejected paths

- rejected path:
  - forcing F411 proof windows to match STM32F103 without measurement
  - why it was rejected:
    - live captures showed the F411 proof cadence is different even though the methodology is the same
- rejected path:
  - treating the SPI failure as another proof-window issue
  - why it was rejected:
    - the SPI proof stayed low even though the generic F411 self-check pattern was already validated elsewhere
- rejected path:
  - assuming that the SPI path is fully working because `PA3` toggles
  - why it was rejected:
    - `PA3` only proves the software transfer path is reached; it does not prove external `PB13` clock visibility or stable loopback success
- rejected path:
  - rewriting the F411 SPI implementation before first resolving the physical `PB13/PB14` path
  - why it was rejected:
    - the direct `PB13` GPIO probe gave a cleaner hardware/wiring verdict than speculative SPI register changes

## Lessons learned

- what succeeded:
  - the staged methodology transfer from STM32F103 works well on F411 when the implementation is rebuilt from official F411 headers/startup
  - one fixed proof-pin strategy on `PA2` works for the F411 self-check family
- what failed:
  - the first draft proof windows assumed F103-like proof frequency and caused false verify failures
  - the initial SPI runs were confounded by an actual solder/connectivity fault on `PB13/PB14`
- what was learned:
  - methodology reuse is portable; proof timing is not
  - F411 plans should record the measured proof range rather than inherit F103 thresholds
  - the current bench wiring remains `PA2 -> P0.0`, `PA3 -> P0.1`, `PB13 -> P0.2`
  - temporary direct pin probes are the fastest way to separate bench faults from peripheral-config faults
  - once the physical `PB13/PB14` issue was fixed, the SPI implementation and loopback path behaved as expected

## Recommended next step

- next safest implementation step:
  - clean up the temporary SPI debug targets/plans now that the root cause is understood
  - keep the SPI proof window at the measured F411 range rather than the earlier F103-like default
- next safest validation step:
  - rerun the full F411 suite after SPI cleanup to confirm the board is now fully stable
- current overall status:
  - F411 bring-up round 2 is effectively complete: the GPIO signature baseline and all first-pass self-check tests now pass on live hardware
