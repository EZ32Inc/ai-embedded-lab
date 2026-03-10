# STM32F411CEU6 target provenance

This target was refreshed from official ST STM32CubeF4 sources and keeps AEL-owned
test logic in `main.c`.

Upstream source:
- repo: `https://github.com/STMicroelectronics/STM32CubeF4.git`
- cached at: `third_party/cache/STM32CubeF4`
- revision: `b782cde5476d2a1fb0ac02c0d64a3a991a35e04f`
- describe: `v1.28.3-8-gb782cde54`

Copied ST files:
- `Drivers/CMSIS/Device/ST/STM32F4xx/Source/Templates/gcc/startup_stm32f411xe.s`
  -> `vendor/st/startup_stm32f411xe.s`
- `Drivers/CMSIS/Device/ST/STM32F4xx/Source/Templates/system_stm32f4xx.c`
  -> `vendor/st/system_stm32f4xx.c`
- `Drivers/CMSIS/Device/ST/STM32F4xx/Include/stm32f4xx.h`
  -> `vendor/include/st/stm32f4xx.h`
- `Drivers/CMSIS/Device/ST/STM32F4xx/Include/stm32f411xe.h`
  -> `vendor/include/st/stm32f411xe.h`
- `Drivers/CMSIS/Device/ST/STM32F4xx/Include/system_stm32f4xx.h`
  -> `vendor/include/st/system_stm32f4xx.h`

AEL-owned files:
- `main.c`
- `Makefile`
- `stm32f411.ld`
- `provenance.md`

Local AEL decisions:
- `main.c` implements the GPIO golden signature pattern using official CMSIS
  register definitions rather than hand-defined addresses.
- the linker script uses the official STM32F411xE memory template values:
  `FLASH 0x08000000..0x0807FFFF` and `RAM 0x20000000..0x2001FFFF`
  as shown in ST's `stm32f411xe_flash.icf`.
- the GCC startup file is used unchanged; AEL provides an empty
  `__libc_init_array()` because this target does not use C++ constructors or a
  hosted C runtime.
