# describe_test_stm32f401_001

## Question

Please show me stm32f401rct6 golden GPIO test connections and what will be tested.

## Approved Answer Draft

STM32F401RCT6 golden GPIO test:

- board: stm32f401rct6
- test: gpio_signature
- probe: ESP32JTAG

Connections:
- SWD -> P3
- RESET -> NC
- PA4 -> P0.0
- PA3 -> P0.1
- PA2 -> P0.2
- PA1 -> P0.3
- PC13 -> LED

What will be tested:
- signal validation on PA4 through the generic sig path
- duration: 1.0 s
- expected frequency range: 200 Hz .. 100000 Hz
- expected duty range: 0.4 .. 0.6
- minimum edges: 2
- maximum edges: 20000

Current limitation:
- this test currently validates the single generic signal path, not all toggled pins individually

## Retrieval Path

- `python3 -m ael inventory describe-test --board stm32f401rct6 --test tests/plans/gpio_signature.json`
