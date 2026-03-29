# Skill: Start STM32F401 Rule-B Suite Without Replacing The Legacy Pack

## Trigger

Use this when:
- STM32F401 already has a working older golden pack
- a new Rule-B suite needs to begin
- the goal is to preserve the legacy pack while adding the newer staged suite

## Rule

Do not mutate the preserved older pack into Rule-B.

Instead:
- leave the older pack runnable as historical truth
- add a new Rule-B Stage 0 pack beside it
- validate the new Stage 0 on hardware before adding more stages

## Implementation Pattern

1. Keep the preserved legacy pack unchanged.
2. Add a new Stage 0 test and pack with Rule-B naming.
3. If Stage 0 is operator-visible only, define it as `program_only`.
4. Do not route a visual LED-only Stage 0 through generic LA verification.
5. Update the board note so the two-suite policy is explicit.

## STM32F401-Specific Lesson

For `STM32F401RCT6`:
- preserved legacy pack: `packs/smoke_stm32f401.json`
- new Rule-B bootstrap pack: `packs/stm32f401rct6_stage0.json`

The visual LED baseline should use:
- `tests/plans/stm32f401rct6_pc13_blinky_visual.json`
- `test_kind: program_only`

Reason:
- board observe map may contain `led: LED` for human-visible routing
- generic verify logic expects LA pins such as `P0.x`
- treating `LED` as an LA bit causes a false integration failure

## Reusable Lesson

When starting Rule-B on a board with an older proven suite:
- preserve first
- add the new suite in parallel
- use the smallest truthful Stage 0
- do not let convenience verification paths distort the meaning of a visual-only baseline
