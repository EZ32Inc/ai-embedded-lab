# Boards

This directory contains board-specific notes and dated board closeouts.

Use these docs to understand board identity, wiring assumptions, observed
bring-up behavior, and historical validation evidence. For current runnable
tests, verify against inventory, packs, manifests, and target configs in the
repository.

## Board Notes

| Board | Document |
|---|---|
| ESP32-C5 devkit | [esp32c5_bringup_notes.md](./esp32c5_bringup_notes.md) |
| ESP32-C6 devkit | [esp32c6_bringup_notes.md](./esp32c6_bringup_notes.md) |
| STM32F030C8T6 | [stm32f030c8t6.md](./stm32f030c8t6.md) |
| STM32F103C6T6 bluepill-like | [stm32f103c6t6_bluepill_like.md](./stm32f103c6t6_bluepill_like.md) |
| STM32F103RCT6 | [stm32f103rct6.md](./stm32f103rct6.md) |
| STM32F401RCT6 | [stm32f401rct6.md](./stm32f401rct6.md) |
| STM32F411CEU6 | [stm32f411ceu6.md](./stm32f411ceu6.md) |

## Dated Closeouts

Closeout files in this directory record a specific validation result. They are
useful evidence, but they should be checked against the current code and test
packs before being cited as current support.

## Maintenance Rules

- Keep board fact sheets separate from closeouts.
- Add new boards as concise fact sheets first.
- Link detailed validation evidence from `docs/reports/` when possible.
- Avoid bench-local paths, private IP addresses, and serial numbers in public
  board docs.
