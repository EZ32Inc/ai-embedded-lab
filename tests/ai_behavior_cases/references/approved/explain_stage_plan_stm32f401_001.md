# explain_stage_plan_stm32f401_001

## Question

What's in plan?

## Approved Answer Draft

For this STM32F401RCT6 path, plan includes configuration and execution-shape resolution, not real hardware validation.

Plan includes:
- selected board: stm32f401rct6
- selected test: gpio_signature
- selected probe path: ESP32JTAG
- resolved wiring assumptions: swd=P3, reset=NC, verify=P0.0
- resolved board clock: 16000000 Hz
- resolved board observe map: sig->P0.0, pa4->P0.0, pa3->P0.1, pa2->P0.2, pa1->P0.3, led->LED
- resolved verification views: signal->P0.0, led->LED
- selected builder kind: arm_debug
- selected firmware project: firmware/targets/stm32f401rct6
- selected check model: signal verification on sig

What plan does not prove:
- probe reachability
- DUT connection correctness
- SWD function on the real board
- flash success
- PA4 toggling on hardware
- overall real-hardware test pass

## Retrieval Path

- `python3 -m ael explain-stage --board stm32f401rct6 --test tests/plans/gpio_signature.json --stage plan`
