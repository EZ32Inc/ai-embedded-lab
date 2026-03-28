# STM32F103C6T6 Bluepill-like Bring-Up Closeout 2026-03-28

## Scope

First exact-MCU bring-up for a Bluepill-like board using:

- MCU: `STM32F103C6T6`
- debug interface: `SWD`
- instrument: `ESP32JTAG`
- endpoint: `192.168.2.106:4242`
- visible LED net: user-stated `PC13`

## Identification Gate Outcome

This bring-up did not proceed until the MCU was identified exactly as
`STM32F103C6T6`.

Board model remained approximate (`Bluepill-like`), but that was acceptable
because:

- the exact MCU part number was confirmed by user-provided silk marking
- the user also explicitly stated the board-level LED expectation on `PC13`

## Setup Confirmation Outcome

Confirmed setup before execution:

- MCU: `STM32F103C6T6`
- board style: Bluepill-like
- target LED: `PC13`
- debug interface: `SWD`
- instrument: ESP32JTAG
- instrument IP: `192.168.2.106`
- target power: on

## What Was Added

- exact board profile:
  [stm32f103c6t6_bluepill_like.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/boards/stm32f103c6t6_bluepill_like.yaml)
- exact-MCU target wrapper with correct memory map:
  [Makefile](/nvme1t/work/codex/ai-embedded-lab/firmware/targets/stm32f103c6_gpio_no_external_capture/Makefile)
  [startup.c](/nvme1t/work/codex/ai-embedded-lab/firmware/targets/stm32f103c6_gpio_no_external_capture/startup.c)
  [stm32f103c6.ld](/nvme1t/work/codex/ai-embedded-lab/firmware/targets/stm32f103c6_gpio_no_external_capture/stm32f103c6.ld)
- exact test plan:
  [stm32f103c6_gpio_no_external_capture.json](/nvme1t/work/codex/ai-embedded-lab/tests/plans/stm32f103c6_gpio_no_external_capture.json)

## Why A New Exact-MCU Wrapper Was Needed

The existing generic STM32F103 mailbox/self-check target was not safe to reuse
blindly for `STM32F103C6T6` because it assumed:

- `64 KB` flash
- `20 KB` RAM
- stack top `0x20005000`

Those values exceed the exact `STM32F103C6T6` device limits. For this session,
an exact wrapper was added with:

- `32 KB` flash
- `10 KB` RAM
- stack top `0x20002800`

This avoided proceeding on an unstated density assumption.

## Flash / Probe Path

The validated BMDA sequence for this board profile is:

- `file {firmware}`
- `monitor swdp_scan`
- `attach {target_id}`
- `load`
- `attach {target_id}`
- `detach`

## Validation Run

- run id:
  `2026-03-28_19-25-36_stm32f103c6t6_bluepill_like_stm32f103c6_gpio_no_external_capture`
- result: `PASS`

Artifacts:

- [result.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-28_19-25-36_stm32f103c6t6_bluepill_like_stm32f103c6_gpio_no_external_capture/result.json)
- [verify_result.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-28_19-25-36_stm32f103c6t6_bluepill_like_stm32f103c6_gpio_no_external_capture/artifacts/verify_result.json)

## Conclusion

The new `STM32F103C6T6` board path flashed and ran successfully on the live
ESP32JTAG bench using only SWD, with exact MCU identification and an exact
memory-map wrapper rather than a generic STM32F103 density assumption.
