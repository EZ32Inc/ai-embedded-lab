# Default Verification Single-Run Triage

## Purpose

This skill defines a low-blast-radius workflow for validating a changed path through the real `verify-default` entrypoint without running the whole default baseline.

Its primary use is to answer:

- did a recent schema / inventory / explain / selection change break the real entrypoint?
- is a failure really a bench/runtime problem, or only a control-plane bug?
- which layer should be debugged next?

## Why This Skill Exists

This skill was extracted from the 2026-03-19 schema-advisory validation round.

The first meter-backed `verify-default single_run` looked like a flash or meter-path failure.
It was not.

The real issue was an adapter bug in `ael/adapter_registry.py`:

- ESP-IDF flash completed successfully
- `flash.log` showed verified writes
- the run still failed because `_LoadAdapter.execute()` referenced an undefined local `payload`

Without a disciplined single-run review, this could easily have been misclassified as:

- meter instability
- ESP-IDF flashing instability
- schema migration fallout

The actual lesson is that `verify-default single_run` is an excellent separator between:

- entrypoint selection problems
- adapter/control-plane bugs
- true bench/runtime failures

## Trigger / When To Use

Use this skill when:

- a plan schema or inventory surface changed
- `supported_instruments` or test-kind behavior changed
- a new `instrument_specific` plan was formalized
- a representative path should be checked through the real default-verification entrypoint
- a fresh `verify-default` failure needs classification before deeper debugging

## Inputs

- target board id
- target test plan path
- repo root
- optional temporary single-run config path
- latest run directory and logs if a failure already happened

## Core Procedure

1. Build a temporary `verify-default` config with `mode: single_run`.
   Example shape:

   ```json
   {
     "mode": "single_run",
     "board": "esp32c6_devkit",
     "test": "tests/plans/esp32c6_gpio_signature_with_meter.json",
     "version": 1
   }
   ```

2. Pick one representative path, not the whole baseline.
   Good choices:
   - one mailbox-style path
   - one instrument-specific path

3. Run:

   ```bash
   PYTHONPATH=. python3 -m ael verify-default run --file /tmp/<single_run>.json
   ```

4. Classify the result in this order:
   - Did the entrypoint select the expected board, instrument, and test?
   - Did build start and complete?
   - Did load/flash actually succeed?
   - Did check/verify run?
   - Is the failure label consistent with the underlying evidence?

5. If the stage label and low-level log disagree, inspect these files together:
   - run `result.json`
   - `artifacts/result.json`
   - `flash.log`
   - `verify.log`

6. Separate the failure into one of these buckets:
   - entrypoint/selection
   - adapter/control-plane
   - build/toolchain
   - load/flash
   - verify/runtime
   - bench/resource reachability

## Key Rule

Do not trust the top-level stage label by itself.

If stdout says `stage=flash` failed, but `flash.log` shows verified writes, the real issue may be:

- adapter exception after success
- bad stage mapping
- result-normalization bug

Always cross-check:

- top-level run summary
- step-level artifact result
- low-level stage log

## What This Skill Prevents

It prevents common false leads such as:

- blaming schema changes for a runtime adapter bug
- blaming the bench for a post-success exception
- blaming the instrument when build/load already proved selection was correct

## Recommended Decision Pattern

If `single_run` fails:

1. confirm entrypoint selection is correct
2. inspect `result.json`
3. inspect `artifacts/result.json`
4. inspect the stage log named by the failure
5. only then decide whether to debug:
   - plan metadata
   - adapter code
   - instrument reachability
   - DUT/runtime behavior

## Evidence Pattern From The Source Case

Source case:
- board: `esp32c6_devkit`
- test: `tests/plans/esp32c6_gpio_signature_with_meter.json`
- initial failed run: `2026-03-19_21-29-20_esp32c6_devkit_esp32c6_gpio_signature_with_meter`
- fixed pass run: `2026-03-19_21-37-29_esp32c6_devkit_esp32c6_gpio_signature_with_meter`

What separated the real cause from the false lead:
- `flash.log` proved the write succeeded
- `artifacts/result.json` showed repeated adapter exceptions at load
- `result.json` named the real Python error: `local variable 'payload' referenced before assignment`

## Success Criteria

This skill is successful when:

- a changed path is validated through the real default-verification entrypoint
- the failure is assigned to the right layer
- false bench-level conclusions are avoided
- the next debug action is obvious and justified by evidence

## Output Expectations

At minimum, report:

- the selected representative path
- whether the entrypoint selection was correct
- pass/fail outcome
- run id
- failure layer classification
- the specific evidence that ruled out the main false lead

## Relationship To Adjacent Skills

- `default_verification_review_skill.md` explains whole-baseline interpretation
- this skill is narrower and earlier: single-path entrypoint validation and triage
- `late_verify_failure_interpretation.md` starts after a real verify failure is known
- this skill helps decide whether the failure is even a real verify failure
