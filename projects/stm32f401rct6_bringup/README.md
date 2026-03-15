# STM32F401RCT6 8-experiment bringup

## User Goal

Run all 8 banner experiments: GPIO signature, UART, SPI, ADC, Capture, EXTI, GPIO loopback, PWM

## Current Status

- status: `shell_created`
- path_maturity: `mature` (confidence: high)
- target MCU: `stm32f401rct6`
- closest mature AEL path: `stm32f401rct6`
- domain: `user_project_domain`
- project user: `local_user`

## Confirmed Facts

- User requested a project for stm32f401rct6

## Assumptions

- The user's board matches the known mature stm32f401rct6 path in the AEL repo

## Unresolved Items

- Board variant confirmation — which exact board/variant do you have? (repo reference: stm32f401rct6)
- Instrument confirmation — what debug/flash instrument are you using?
- Wiring/connections confirmation — does your bench wiring match the repo bench_setup?
- Intended first test — what should the first test demonstrate?

## Best Next Questions

- What exact setup/wiring is available for this board?
- What first example should be generated?
- What validation approach should be used first?
