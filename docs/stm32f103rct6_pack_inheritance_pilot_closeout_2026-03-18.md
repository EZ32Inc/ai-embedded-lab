# STM32F103RCT6 Pack Inheritance Pilot Closeout

Date: 2026-03-18
Status: Partial Pass

## Scope

This note records the first live validation round for the minimal pack
inheritance (`extends`) pilot using STM32F103RCT6 mailbox smoke packs.

Related note:

- [pack_inheritance_minimal_v0_1.md](./pack_inheritance_minimal_v0_1.md)

## Pilot Structure

Base pack:

- `packs/smoke_stm32f103rct6_mailbox_base.json`

Child packs:

- `packs/smoke_stm32f103rct6_mailbox_esp32jtag.json`
- `packs/smoke_stm32f103rct6_mailbox_stlink.json`

Shared content kept in base pack:

- shared mailbox test selection
- shared firmware target and mailbox plan path

Instrument-specific execution kept in child packs:

- selected board path
- control instrument path resolved through the selected board profile

## Validation Outcome

### ST-Link child pack

Command path:

- `python3 -m ael pack --pack packs/smoke_stm32f103rct6_mailbox_stlink.json`

Result:

- `PASS`
- run id: `2026-03-18_21-21-43_stm32f103rct6_stlink_stm32f103rct6_mailbox`

Interpretation:

- the child pack resolved correctly to board `stm32f103rct6_stlink`
- the inherited shared mailbox test executed correctly through the ST-Link path
- the pilot proved that shared firmware/test can stay in the base pack while execution selection stays in the child pack

### ESP32-JTAG child pack

Command path:

- `python3 -m ael pack --pack packs/smoke_stm32f103rct6_mailbox_esp32jtag.json`

Result:

- `FAIL`
- failure stage: `flash`

Observed runtime failure:

- repeated `No route to host` while trying to reach `192.168.2.109:4242`

Interpretation:

- the child pack still resolved correctly to board `stm32f103rct6`
- the failure was a live bench/instrument reachability issue, not an inheritance-resolution issue
- no change to `extends` semantics is needed based on this result

## Decision

The inheritance pilot is good enough to continue using in narrow scope because:

- pack loading and inheritance behaved as intended
- one live child path passed end-to-end
- the failing child path failed for a runtime connectivity reason outside pack structure

The new mailbox child packs remain pilot-only for now.
The older broad smoke packs remain the current canonical STM32F103RCT6 paths.

## Next Debug Focus

For the ESP32-JTAG child path, debug only:

- control instrument reachability at `192.168.2.109:4242`
- target power and network path to the instrument
- bench-side availability of the STM32 golden ESP32-JTAG node

Do not widen `extends` semantics until that runtime path is healthy.
