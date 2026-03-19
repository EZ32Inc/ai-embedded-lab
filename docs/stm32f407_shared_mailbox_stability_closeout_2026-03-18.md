## STM32F407 Shared Mailbox Stability Closeout

Date: 2026-03-18

Scope:
- Shared mailbox firmware/test on STM32F407 across multiple instruments
- Formal pack entry under:
  - `packs/smoke_stm32f407_mailbox_esp32jtag.json`
  - `packs/smoke_stm32f407_mailbox_stlink.json`

ESP32-JTAG stability result:
- `STM32F407 + ESP32-JTAG` pack was repeated 5 times
- Result: 5 / 5 pass
- Run ids:
  - `2026-03-18_22-21-57_stm32f407_discovery_esp32jtag_stm32f407_mailbox`
  - `2026-03-18_22-22-12_stm32f407_discovery_esp32jtag_stm32f407_mailbox`
  - `2026-03-18_22-22-27_stm32f407_discovery_esp32jtag_stm32f407_mailbox`
  - `2026-03-18_22-22-42_stm32f407_discovery_esp32jtag_stm32f407_mailbox`
  - `2026-03-18_22-22-57_stm32f407_discovery_esp32jtag_stm32f407_mailbox`

ST-Link symmetric rerun status:
- `STM32F407 + ST-Link` pack was repeated 5 times
- Result: 5 / 5 pass
- Run ids:
  - `2026-03-18_22-27-16_stm32f407_discovery_stm32f407_mailbox`
  - `2026-03-18_22-27-25_stm32f407_discovery_stm32f407_mailbox`
  - `2026-03-18_22-27-34_stm32f407_discovery_stm32f407_mailbox`
  - `2026-03-18_22-27-44_stm32f407_discovery_stm32f407_mailbox`
  - `2026-03-18_22-27-53_stm32f407_discovery_stm32f407_mailbox`

Interpretation:
- The new formal ESP32-JTAG pack is stable for repeated mailbox-smoke execution
- The shared mailbox test remains reusable across instruments
- The symmetric ST-Link pack is also stable for repeated mailbox-smoke execution
- The shared mailbox firmware/test model is now validated on STM32F407 across both supported instrument paths in repeated live runs

Next recommended action:
- Treat the STM32F407 mailbox shared-pack pattern as validated
- Reuse the same pattern for the next board family only when there is a concrete need
