# STM32 Operator Note

This is the current quick reference for the STM32 golden GPIO bench paths.

## Probe

- Probe: `ESP32JTAG`
- Probe IP: `192.168.2.98`
- SWD hookup: `SWD -> P3`
- RESET hookup: `RESET -> NC`

## STM32F401RCT6

Bench wiring:
- `PA4 -> P0.0`
- `PA3 -> P0.1`
- `PA2 -> P0.2`
- `PC13 -> P0.3`
- `PC13 -> LED`

Expected behavior:
- `PA4`, `PA3`, and `PA2` toggle for the golden GPIO waveform path
- `PC13` blinks every `0.5 s`

Useful commands:
```bash
python3 -m ael inventory describe-test --board stm32f401rct6 --test tests/plans/gpio_signature.json
python3 -m ael explain-stage --board stm32f401rct6 --test tests/plans/gpio_signature.json --stage plan
python3 -m ael run --board stm32f401rct6 --test tests/plans/gpio_signature.json
python3 -m ael run --board stm32f401rct6 --test tests/plans/stm32f401_led_blink.json
```

Latest known-good golden GPIO run:
- run id: `2026-03-09_07-44-47_stm32f401rct6_gpio_signature`
- artifact: `runs/2026-03-09_07-44-47_stm32f401rct6_gpio_signature/result.json`

Notes:
- `inventory describe-test` will warn that `PC13` is connected to both `P0.3` and `LED`.
- Do not add `continue` to the STM32F401 custom `gdb_launch_cmds`; that left SWD busy and broke the working flash path.

## STM32F103

Bench wiring:
- `PA4 -> P0.0`
- `PA5 -> P0.1`
- `PA6 -> P0.2`
- `PA7 -> P0.3`
- `PC13 -> LED`

Expected behavior:
- `PA4` through `PA7` toggle for the golden GPIO waveform path
- `PC13` blinks every `0.5 s`

Useful commands:
```bash
python3 -m ael inventory describe-test --board stm32f103 --test tests/plans/gpio_signature.json
python3 -m ael explain-stage --board stm32f103 --test tests/plans/gpio_signature.json --stage plan
python3 -m ael run --board stm32f103 --test tests/plans/gpio_signature.json
```

Latest known-good golden GPIO run:
- run id: `2026-03-09_07-51-57_stm32f103_gpio_signature`
- artifact: `runs/2026-03-09_07-51-57_stm32f103_gpio_signature/result.json`
