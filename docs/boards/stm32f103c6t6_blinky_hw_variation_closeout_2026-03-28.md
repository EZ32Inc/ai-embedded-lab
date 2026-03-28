# STM32F103C6T6 Blinky And Hardware Variation Closeout 2026-03-28

## Scope

Closeout for `STM32F103C6T6` Bluepill-like LED bring-up on the ESP32JTAG bench
 at `192.168.2.106`, after multiple same-type boards showed inconsistent
 visible behavior.

## Confirmed Setup

- board class: Bluepill-like
- MCU: `STM32F103C6T6`
- LED net: `PC13` (user-stated for this board type)
- debug interface: `SWD`
- instrument: `ESP32JTAG`
- endpoint: `192.168.2.106:4242`
- normal boot mode for flash/run: `BOOT0=0`, `BOOT1=0`

## What Happened

Several same-type boards were tried.

Observed pattern:

- some boards accepted flash traffic but did not produce trustworthy LED
  behavior
- one board showed a clean flash/run and the minimal reference-style `PC13`
  blinky became visibly correct

This means the session produced evidence of both:

- firmware-side diagnostic weakness in the earlier test image
- board-level hardware variation or board-specific fault on some units

## Firmware Lesson

The earlier `STM32F103C6T6` image was not a clean LED-only diagnostic. It still
contained mailbox/self-test structure inherited from the prior path.

That made LED interpretation weaker than necessary.

The accepted baseline is now the minimal reference-style `PC13` blinky in:

- [main.c](/nvme1t/work/codex/ai-embedded-lab/firmware/targets/stm32f103c6_gpio_no_external_capture/main.c)

Properties of the accepted baseline:

- `PC13` only
- `BSRR` set/reset writes
- active-low LED assumption matching common Bluepill behavior
- simple delay loop
- no mailbox logic
- no extra GPIO bus activity

## Hardware Lesson

Same-type Bluepill-like boards are not interchangeable by assumption.

During this session:

- some boards did not yield reliable visible LED evidence
- another board of the same claimed type did blink correctly with the exact same
  firmware and bench path

So future work should separate:

- board-type identification
- exact MCU identification
- known-good physical unit validation

## Known-Good Baseline

Accepted firmware baseline:

- commit `a515dd2`
- message: `Use reference-style STM32F103C6 PC13 blinky`

Accepted live run on a known-good board:

- `2026-03-28_19-52-06_stm32f103c6t6_bluepill_like_stm32f103c6_gpio_no_external_capture`

Artifacts:

- [result.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-28_19-52-06_stm32f103c6t6_bluepill_like_stm32f103c6_gpio_no_external_capture/result.json)

## Recommended Rule For Next Time

Before debugging a new Bluepill-like `STM32F103C6T6` board in depth:

1. start from the minimal reference-style `PC13` blinky
2. validate on one known-good physical board first
3. only then treat failures on another board as likely hardware variation or
   board fault

## Conclusion

This session established a trustworthy `STM32F103C6T6` firmware baseline and
also showed that same-type low-cost boards can differ enough that hardware
variation must be treated as a real factor during bring-up.
