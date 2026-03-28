# STM32F401RCT6 Blink BMDA Closeout 2026-03-28

## Scope

Live validation and debug closeout for `STM32F401RCT6` onboard LED blink on an
ESP32JTAG bench at `192.168.2.106`.

Board facts confirmed during this session:
- MCU: `STM32F401RCT6`
- visible onboard LED on `PC13`
- only `SWD` connected for this task
- no extra loopback or reset wiring used

## What Was Validated

- firmware flash over ESP32JTAG BMDA
- target start/run behavior immediately after flash
- visible onboard LED blink on `PC13`
- operator-confirmed blink-rate changes on live hardware

## Runs

- `2026-03-28_18-51-23_stm32f401rct6_stm32f401_led_blink`
  - restored historical BMDA attach sequence
  - user confirmed immediate blink after flash
- `2026-03-28_18-52-59_stm32f401rct6_stm32f401_led_blink`
  - doubled blink rate
  - flash/run passed
- `2026-03-28_18-54-20_stm32f401rct6_stm32f401_led_blink`
  - slowed blink to final kept state
  - flash/run passed
  - user confirmed visible behavior

## Root Cause And False Lead Separation

The main debug issue was not firmware bring-up and not board wiring once SWD was
corrected. The critical issue was the post-`load` GDB command sequence used by
the ESP32JTAG BMDA path.

False lead:
- treating `monitor reset run` as the generic correct post-flash action

Evidence against that lead:
- user observed blink only after unplug/replug when the wrong sequence was used
- repo history already contained an STM32 BMDA stabilization commit that added a
  second `attach {target_id}` for `stm32f401rct6`
- restoring the historical sequence made the board blink immediately again

Working sequence for this bench:
- `file -> monitor a -> attach -> load -> attach -> detach`

Non-working sequence in this session:
- `file -> monitor a -> attach -> load -> monitor reset run -> ...`

## Final Kept State

- board config keeps the historical STM32F401 BMDA attach sequence
- firmware keeps the slower blink requested by the user:
  - `PC13` toggles every `1000 ms`
- test expectation updated to `expected_hz: 1.0`

## Files

- [stm32f401rct6.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/boards/stm32f401rct6.yaml)
- [main.c](/nvme1t/work/codex/ai-embedded-lab/firmware/targets/stm32f401rct6/main.c)
- [stm32f401_led_blink.json](/nvme1t/work/codex/ai-embedded-lab/tests/plans/stm32f401_led_blink.json)

## Why This Was Easy To Miss

The failure looked like a generic "target not running after flash" problem, so
it was tempting to apply the common `reset run` intuition. That was weaker than
the local repo evidence and weaker than the user's bench observation.

The guardrail for next time is:
- prefer the known-good board-family BMDA sequence already validated in repo
- treat user-visible post-flash behavior as primary evidence when run-stage
  status alone is ambiguous
- do not replace a bench-specific attach/detach pattern with a generic reset
  pattern without live confirmation

## Conclusion

This STM32F401RCT6 + ESP32JTAG bench is stable for visible LED blink using only
SWD, and it depends on the historical second-attach BMDA sequence rather than
`monitor reset run`.
