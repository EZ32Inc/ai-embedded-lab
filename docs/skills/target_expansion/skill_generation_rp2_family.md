# Skill: Generate RP2-Family Target From Local Reference

## Purpose

Add or expand RP2040/RP2350-family targets by keeping the local AEL RP2 target
shape as the main structural reference.

For the first RP2350 path in a line, use official Pico SDK board/platform
support together with the closest local RP2040 AEL target shape.

## Scope

- RP2040 target expansion
- RP2350 target expansion
- future nearby RP2-family MCU expansion where Pico SDK support exists

## Core rule

- RP2040 future work: generate from the closest validated local RP2040 AEL
  target first
- first RP2350 work: start from official Pico SDK support plus the closest local
  RP2040 AEL target shape
- later RP2350 work: generate from the closest validated local RP2350 AEL
  target first

## Inputs

- new board id and target id
- closest local RP2-family reference target
- official Pico SDK board id if using official board support
- intended GPIO/verify behavior
- intended control-instrument path
- current bench wiring assumptions

## Typical files to inspect and reuse

- `configs/boards/<reference>.yaml`
- `firmware/targets/<reference_target>/`
- `tests/plans/gpio_signature.json` or related test plan
- `assets_golden/duts/<reference_dut>/manifest.yaml`
- `assets_golden/duts/<reference_dut>/docs.md`
- `ael/adapters/build_cmake.py`

## Procedure

1. Inspect the nearest local RP2-family target first.
2. If generating the first RP2350 path, confirm the official Pico SDK board
   identifier and platform.
3. Keep the Pico SDK build structure intact.
4. Copy/adapt the local AEL target shape into a new target directory.
5. Make board-specific updates:
   - target id
   - board id
   - `PICO_BOARD`
   - artifact naming
   - GPIO assumptions
6. Add or update:
   - board config
   - DUT manifest/docs
   - test plan usage
7. Validate through:
   - `inventory describe-test`
   - `explain-stage --stage plan`
   - build-stage confirmation
8. Keep validation status conservative until bench stages are complete.

## Validation flow

1. Static checks: file existence and naming consistency.
2. `inventory describe-test --board <board> --test <test>`
3. `explain-stage --board <board> --test <test> --stage plan`
4. Build confirmation through AEL.
5. Bench stages only when wiring and control-instrument facts are ready.

## Common pitfalls

- hardcoding the RP2040 project path in build logic
- assuming official Pico SDK support means runtime validation is complete
- hiding new board assumptions inside copied local code
- treating board profile identity and DUT validation status as the same thing

## Outputs

- new RP2-family target directory
- new board config
- DUT manifest/docs
- explicit provenance and validation status
- staged readiness summary for follow-up bench work

## Related docs

- [rp2_example_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/rp2_example_generation_policy_v0_1.md)
- [new_board_bringup_and_validation_flow.md](/nvme1t/work/codex/ai-embedded-lab/docs/new_board_bringup_and_validation_flow.md)
