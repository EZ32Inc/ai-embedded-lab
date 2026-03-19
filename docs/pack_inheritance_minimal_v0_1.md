# Pack Inheritance Minimal v0.1

Date: 2026-03-18
Status: Pilot

## Purpose

This note defines the minimal supported `extends` mechanism for AEL packs.

The immediate goal is narrow:

- reduce pack duplication
- keep shared firmware/test selection in one base pack
- keep instrument-specific execution selection in child packs

This is not a general pack refactor.

## Supported Scope

Current support is intentionally minimal:

- single-parent inheritance only
- `extends` must be a string path
- parent path is resolved relative to the child pack file
- child scalar fields override parent scalar fields
- child list fields replace parent list fields
- child dict fields merge recursively

## Non-Goals

This mechanism does not support:

- multiple inheritance
- variable expansion
- template expressions
- include graphs
- global result-contract changes
- pipeline behavior changes

## Pilot Rule

For the STM32F103RCT6 mailbox pilot:

- shared target/firmware/test selection lives in the base pack
- instrument-specific execution selection lives in the child pack
- runtime differences should come from the selected board/instrument path, not from duplicated test lists

## Canonical Path Decision

Current repo policy:

- existing broad smoke packs remain the current canonical paths:
  - `packs/smoke_stm32f103rct6.json`
  - `packs/smoke_stm32f103rct6_stlink.json`
- new mailbox-only child packs are pilot-only for now:
  - `packs/smoke_stm32f103rct6_mailbox_esp32jtag.json`
  - `packs/smoke_stm32f103rct6_mailbox_stlink.json`

Reason:

- the pilot is proving pack structure reuse, not replacing the broader validated smoke suites yet
- canonical-path replacement should happen only after live pilot evidence is recorded
