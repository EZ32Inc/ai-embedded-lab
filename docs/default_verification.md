# Default Verification

Run the current baseline sequence with:

```bash
python3 -m ael verify-default run
```

Stress it with:

```bash
python3 -m ael verify-default repeat-until-fail --limit 20
```

Current default sequence:

1. `esp32c6_golden_gpio`
   - board: `esp32c6_devkit`
   - test: `tests/plans/esp32c6_gpio_signature_with_meter.json`
   - evidence: UART + meter-backed `instrument.signature`
2. `rp2040_golden_gpio_signature`
   - board: `rp2040_pico`
   - test: `tests/plans/gpio_signature.json`
   - probe instance: `esp32jtag_rp2040_lab`
   - evidence: logic-analyzer `gpio.signal`
3. `stm32f103_golden_gpio_signature`
   - board: `stm32f103`
   - test: `tests/plans/gpio_signature.json`
   - probe instance: `esp32jtag_stm32_golden`
   - evidence: logic-analyzer `gpio.signal`

Current validated baseline:

- default verification passed `10/10`
- STM32F401 golden GPIO passed `10/10`
- STM32F103 golden GPIO passed `10/10`
- STM32F401 direct post-flash `+5s` stability benchmark passed `20/20`

Known-good comparison artifacts:

- ESP32-C6:
  - `runs/2026-03-09_14-57-25_esp32c6_devkit_esp32c6_gpio_signature_with_meter/artifacts/evidence.json`
- RP2040:
  - `runs/2026-03-09_14-58-12_rp2040_pico_gpio_signature/artifacts/evidence.json`
- STM32F103:
  - `runs/2026-03-09_14-58-42_stm32f103_gpio_signature/artifacts/evidence.json`

Legacy note:

- old raw probe configs such as `configs/esp32jtag.yaml` are still accepted
- they now warn: `Using legacy shared probe config; explicit instrument instance is recommended.`
