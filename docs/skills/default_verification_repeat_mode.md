# Default Verification Repeat Mode

## 1. Purpose

This document explains how repeated default verification should be run in AEL and how to interpret the two different repeat styles.

Its main goal is to prevent confusion between:
- repeating the whole suite process
- repeating each worker independently

## 2. Scope

Use this document when:
- choosing how to run default verification multiple times
- interpreting repeat behavior from logs
- deciding whether the observed pacing is expected

This document is about:
- `python3 -m ael verify-default run`
- `python3 -m ael verify-default repeat --limit N`
- `python3 -m ael verify-default repeat-until-fail --limit N`
- outer shell loops around `verify-default run`

Live-bench validity rule:

- do not do sandbox trial runs first for real-bench `verify-default` commands
- if bench access is blocked before the suite reaches real hardware, classify
  the run as `INVALID`
- do not mix `INVALID` runs into pass/fail reliability judgments

## 3. Background

The default verification suite is now a parallel suite of independent workers.

That means repeated baseline validation has two different operational meanings:
- repeat the suite process as a whole
- repeat each worker on its own worker timeline

These are not equivalent.

Current preferred behavior:
- repeated default verification should use worker-level repetition

## 4. Failure / Issue Classes

### A. Suite-level repetition mistaken for worker-level repetition

Typical symptom:
- the next repeated run does not start until all tasks in the previous run finish

Meaning:
- an outer loop around `verify-default run` is being used

### B. Worker-level repetition misunderstood as synchronized rounds

Typical symptom:
- one board is already on iteration 3 while another is still on iteration 1

Meaning:
- this is expected in worker-level repeat mode

### C. Real shared-resource waiting

Typical symptom:
- one worker cannot advance because it is waiting for a shared resource used by another worker

Meaning:
- this may be correct behavior if the shared dependency is real

## 5. Required Observations

Collect these before explaining repeat behavior:
- command used
- whether `verify-default run` or `verify-default repeat` was used
- execution policy shown in output
- per-worker iteration counts
- whether a worker finished multiple iterations while another lagged
- whether any resource-sharing explanation is backed by real lock/resource facts

## 6. Diagnosis Workflow

1. Identify the command shape first.
   - `verify-default run`
   - `verify-default repeat --limit N`
   - outer shell loop around `verify-default run`

2. If `verify-default run` was used, expect one iteration per worker.

3. If `verify-default repeat --limit N` was used, expect each worker to keep its own iteration counter.

4. If an outer shell loop was used, expect whole-suite pacing.

5. If one worker appears delayed, check whether a real shared resource explains it.

6. Do not describe worker-level repeat output as “round-based” unless the logs actually show synchronized suite rounds.

## 7. Interpretation Guide

- `verify-default run`:
  - one suite pass
  - each worker runs once
  - `INVALID` if the bench was not actually reachable

- `verify-default repeat --limit N`:
  - preferred repeated-run mode
  - each worker repeats independently
  - fast workers can advance without waiting for slow unrelated workers
  - count only bench-reachable runs when judging stability

- `verify-default repeat-until-fail --limit N`:
  - compatibility alias for the same worker-level repeat behavior

- outer shell loop around `verify-default run`:
  - repeats the full suite process
  - not the preferred model when each board should keep progressing on its own
  - each suite iteration is meaningful only if it had valid bench access

## 8. Recommended Output Format

When explaining repeat behavior, report:
- command used
- repeat mode classification:
  - `single_suite_run`
  - `worker_level_repeat`
  - `outer_suite_loop`
- validity classification:
  - `PASS`
  - `FAIL`
  - `INVALID`
- whether worker progression was independent
- whether any delay came from real shared resources
- next recommended command if the current mode was not the desired one

## 9. Current Known Conclusions

- `python3 -m ael verify-default repeat --limit N` is the preferred repeated baseline command.
- `repeat-until-fail` remains a compatibility alias.
- outer shell loops around `verify-default run` are valid, but they are not the preferred repeated-run model for independent board progression.
- independent worker progress is the desired operational behavior where no real shared resource exists.

## 10. Unresolved Questions

- Which repeated-run scenarios should still receive stronger automated coverage?
- Should future reporting make the difference between suite-level and worker-level repeat even more explicit?

## 11. Related Files

- [docs/default_verification.md](/nvme1t/work/codex/ai-embedded-lab/docs/default_verification.md)
- [docs/default_verification_execution_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/default_verification_execution_model.md)
- [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [ael/verification_model.py](/nvme1t/work/codex/ai-embedded-lab/ael/verification_model.py)

## 12. Notes

- This document explains operational meaning, not just command syntax.
- Prefer worker-level repeat when collecting stability data for the default suite.
