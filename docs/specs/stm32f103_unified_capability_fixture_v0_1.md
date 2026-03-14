# STM32F103 Unified Capability Fixture v0.1

Purpose:
- define the current unified STM32F103 fixture used for bounded self-check capability demos with minimal rewiring

## Board role
- primary sample-board capability anchor

## Wiring classification

| Wiring / pin role | Role | Presence | Observation model | Fixture status |
| --- | --- | --- | --- | --- |
| `PA4 -> P0.0` | unified machine-checkable proof output | always-present | externally observed | preserved |
| `PA5 -> P0.1` | auxiliary observe for selected demos | optional | externally observed | optional |
| `PC13 -> LED` | coarse visual status/debug | always-present | externally observed by human only | preserved |
| `PA1 -> PA0` | ADC closed-loop source to ADC input | always-present | internal-only self-check loopback | preserved |
| `PA9 -> PA10` | USART1 TX/RX loopback | always-present | internal-only self-check loopback | preserved |
| `PA7 -> PA6` | SPI MOSI/MISO loopback | always-present for the unified capability fixture | internal-only self-check loopback | preserved |
| `PA8 -> PB8` | timing-class loopback for PWM/GPIO/EXTI/capture | always-present for the unified capability fixture | internal-only self-check loopback | preserved |
| `GND -> probe GND` | common reference ground | always-present | externally required support wiring | preserved |

## Always-preserved external observe path
- `PA4 -> P0.0`
- optional auxiliary observe:
  - `PA5 -> P0.1`
- `PC13 -> LED`
- `GND -> probe GND`

For unified self-check demos:
- `PA4` remains the main external machine-checkable status/output path unless there is a strong reason to change it

## Preserved ADC closed-loop path
- loopback wire:
  - `PA1 -> PA0`
- roles:
  - `PA1` = loopback source
  - `PA0 / ADC1_IN0` = ADC input
- firmware behavior:
  - firmware samples `PA0`
  - firmware interprets ADC result
  - firmware mirrors ADC-validated result onto `PA4`
- external observation:
  - AEL observes `PA4`

## SPI self-check path
- `PA5 = SPI1_SCK`
- `PA7 = SPI1_MOSI`
- `PA6 = SPI1_MISO`
- loopback wire:
  - `PA7 -> PA6`
- SPI pins are treated as:
  - SPI-internal self-check wiring only
- external observation:
  - SPI pass/fail should be encoded onto `PA4`
  - ESP32JTAG should observe `PA4`, not directly capture `PA5/PA6/PA7` as the main proof path
- note:
  - prefer software NSS / no external NSS dependency for the bounded self-check

## UART loopback path
- loopback wire:
  - `PA9 -> PA10`
- roles:
  - `PA9 = USART1_TX`
  - `PA10 = USART1_RX`
- note:
  - on the unified fixture, UART loopback can be an internal self-check path
  - external observation should still prefer the unified bounded status path when possible

## Second-wave path
- reserved loopback:
  - `PA8 -> PB8`
- intended use:
  - PWM self-check
  - GPIO output self-check
  - EXTI self-check
  - input-capture/timing self-check if practical

## Reserved / exploratory only
- I2C remains reserved/exploratory
- likely pins:
  - `PB6 = I2C1_SCL`
  - `PB7 = I2C1_SDA`
- reason it is not immediate focus:
  - likely requires pull-up resistors
  - open-drain behavior adds setup/electrical risk

## Fixture rule
- preserve already-proven paths when adding the next bounded capability demo
- prefer minimal extra wiring
- prefer DUT-internal self-check plus `PA4` as the external machine-checkable result
- keep working pins and observe pins separated:
  - working pins perform the protocol/self-check on the DUT
  - `PA4` remains the default externally observed proof line
- do not require `PA6 -> P0.2` or `PA7 -> P0.3` for the unified capability fixture
