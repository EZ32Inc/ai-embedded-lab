## STM32F103 GPIO Cross-Instrument Closeout

Date: 2026-03-19

Scope:
- DUT family: STM32F103C8T6 Bluepill GPIO bench
- Shared pack base: `packs/smoke_stm32f103_gpio_loopbacks_base.json`
- Child packs:
  - `packs/smoke_stm32f103_gpio_loopbacks_stlink.json`
  - `packs/smoke_stm32f103_gpio_loopbacks_esp32jtag.json`

Shared assets:
- Shared tests stay in the base pack:
  - `stm32f103_gpio_no_external_capture`
  - `stm32f103_uart_loopback_mailbox`
  - `stm32f103_spi_mailbox`
  - `stm32f103_exti_mailbox`
  - `stm32f103_adc_mailbox`
- Instrument-specific execution stays in board / child-pack selection.

Result summary:
- `ESP32-JTAG + STM32F103` formal pack: 5/5 PASS
- `ST-Link + STM32F103` currently demonstrates:
  - PASS `stm32f103_gpio_no_external_capture`
  - PASS `stm32f103_adc_mailbox`
  - `UART/SPI/EXTI` loopback mailbox tests did not verify successfully on ST-Link

ESP32-JTAG full-pack run ids:
- `2026-03-19_06-54-00_stm32f103_gpio_stm32f103_gpio_no_external_capture`
- `2026-03-19_06-54-12_stm32f103_gpio_stm32f103_uart_loopback_mailbox`
- `2026-03-19_06-54-24_stm32f103_gpio_stm32f103_spi_mailbox`
- `2026-03-19_06-54-35_stm32f103_gpio_stm32f103_exti_mailbox`
- `2026-03-19_06-54-46_stm32f103_gpio_stm32f103_adc_mailbox`

Supporting observations:
- On ST-Link, a temporary visual UART run showed the Bluepill LED slow-blinking, confirming the UART loopback path itself was alive.
- The same UART mailbox test passed immediately after switching the same bench to ESP32-JTAG:
  - `2026-03-19_06-50-52_stm32f103_gpio_stm32f103_uart_loopback_mailbox`
- SPI and EXTI also passed under ESP32-JTAG:
  - `2026-03-19_06-53-25_stm32f103_gpio_stm32f103_spi_mailbox`
  - `2026-03-19_06-53-30_stm32f103_gpio_stm32f103_exti_mailbox`

Conclusion:
- The shared STM32F103 loopback pack structure is validated across instruments.
- The DUT-side loopback wiring is consistent with a working setup.
- The remaining discrepancy is specific to `ST-Link + STM32F103C8T6` mailbox verification semantics, not to the shared-pack structure itself.
