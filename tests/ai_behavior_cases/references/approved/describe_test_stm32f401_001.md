# describe_test_stm32f401_001

## Question

Please show me stm32f401rct6 golden GPIO test connections and what will be tested.

## Approved Answer Draft

STM32F401RCT6 golden GPIO test:

- board: stm32f401rct6
- test: stm32f401_gpio_signature
- probe: ESP32JTAG

Connections:
- SWD -> P3
- RESET -> NC
- PA4 -> P0.0
- PA3 -> P0.1
- PA2 -> P0.2
- PC13 -> P0.3
- PC13 -> LED

What will be tested:
- signal validation on PA4 through the stm32f401-specific GPIO signature path
- duration: 1.0 s
- expected frequency range: 200 Hz .. 100000 Hz
- expected duty range: 0.4 .. 0.6
- minimum edges: 2
- maximum edges: 20000

Current notes:
- this test validates the signal path on PA4, while LED blink is tracked as a separate verification view on P0.3
- inventory warns that PC13 is connected to two observation points: P0.3 and LED

## Retrieval Path

- `python3 -m ael inventory describe-test --board stm32f401rct6 --test tests/plans/stm32f401_gpio_signature.json`
