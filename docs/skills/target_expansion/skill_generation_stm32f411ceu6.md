# STM32F411CEU6 GPIO Golden Target Generation

Current formal method:
- fetch ST's official `STM32CubeF4` source with `tools/fetch_stm32cubef4.sh`
- use the repo-local cache at `third_party/cache/STM32CubeF4`
- copy the device support files from ST into `firmware/targets/stm32f411ceu6/vendor/`
- keep AEL-owned glue in:
  - `firmware/targets/stm32f411ceu6/main.c`
  - `firmware/targets/stm32f411ceu6/Makefile`
  - `firmware/targets/stm32f411ceu6/stm32f411.ld`
  - `firmware/targets/stm32f411ceu6/provenance.md`

Official ST source used:
- startup:
  - `Drivers/CMSIS/Device/ST/STM32F4xx/Source/Templates/gcc/startup_stm32f411xe.s`
- system file:
  - `Drivers/CMSIS/Device/ST/STM32F4xx/Source/Templates/system_stm32f4xx.c`
- device headers:
  - `Drivers/CMSIS/Device/ST/STM32F4xx/Include/stm32f4xx.h`
  - `Drivers/CMSIS/Device/ST/STM32F4xx/Include/stm32f411xe.h`
  - `Drivers/CMSIS/Device/ST/STM32F4xx/Include/system_stm32f4xx.h`
- memory template reference:
  - `Drivers/CMSIS/Device/ST/STM32F4xx/Source/Templates/iar/linker/stm32f411xe_flash.icf`

Board-level AEL assumptions kept separate:
- probe/instrument: `esp32jtag_stm32_golden`
- primary verify signal: `PA4 -> P0.0`
- auxiliary signals: `PA3 -> P0.1`, `PA2 -> P0.2`
- provisional LED assumption: `PC13 -> P0.3` and `PC13 -> LED`

Generation rules:
- do not hand-define raw peripheral base addresses when ST CMSIS headers already provide them
- do not copy ST BSP board-wiring assumptions into AEL
- keep copied ST files under `vendor/`
- record exact upstream revision and copied paths in `provenance.md`

Validation for this target:
- build with `make -C firmware/targets/stm32f411ceu6 clean all`
- validate plan stage with:
  - `python3 -m ael inventory describe-test --board stm32f411ceu6 --test tests/plans/gpio_signature.json`
  - `python3 -m ael inventory describe-connection --board stm32f411ceu6 --test tests/plans/gpio_signature.json`
  - `python3 -m ael explain-stage --board stm32f411ceu6 --test tests/plans/gpio_signature.json --stage plan`

What still needs real hardware confirmation:
- package pin exposure for `PA2`, `PA3`, `PA4`, `PC13`
- whether the actual board LED is on `PC13`
- SWD wiring on the intended bench slot
- full flash and verify behavior on real hardware
