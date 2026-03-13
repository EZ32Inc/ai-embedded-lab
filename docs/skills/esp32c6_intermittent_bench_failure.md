# ESP32-C6 Intermittent Bench Failure

## 1. Purpose

This document is a reusable troubleshooting workflow for intermittent `esp32c6_gpio_signature_with_meter` failures in AEL default verification.

Its job is to help future AEL/Codex/AI users:
- classify the failure correctly
- collect the minimum useful evidence
- separate bench-side instability from architecture issues
- choose the next diagnostic action without guessing

## 2. Scope

Use this workflow when the ESP32-C6 path fails in:
- `python3 -m ael verify-default run`
- `python3 -m ael verify-default repeat --limit N`
- isolated ESP32-C6 reruns using the same meter-backed test

This workflow is specifically for the meter-backed default verification path:
- board: `esp32c6_devkit`
- test: `tests/plans/esp32c6_gpio_signature_with_meter.json`
- instrument: `esp32s3_dev_c_meter`

This workflow is not a general debug guide for all ESP32 boards or all probe-backed GPIO tests.

## 3. Background

The ESP32-C6 default verification path differs from the RP2040 and STM32F103 golden GPIO paths:
- it uses meter-backed verification instead of logic-analyzer `gpio.signal`
- it depends on network reachability to the meter endpoint at `192.168.4.1:9000`
- it also depends on successful flash and on the DUT actually running far enough for UART and instrument verification to succeed

Current working assumption:
- the remaining intermittent failures are more likely localized to the ESP32-C6 bench path than to the parallel worker architecture itself

Known architectural context:
- the default verification worker model is parallel
- repeated default verification should prefer:
  - `python3 -m ael verify-default repeat --limit N`
- current evidence does not support reopening the old false shared-probe explanation as the primary cause

## 4. Failure / Issue Classes

### A. Network / meter reachability failures

Examples:
- `192.168.4.1` unreachable
- ping failure
- TCP connect failure
- HTTP or instrument API failure
- meter doctor or describe commands fail unexpectedly

Typical signature:
- failure occurs early, before flash/verify completes
- error references meter reachability or manual meter checking

### B. Verify-stage failures

Examples:
- flash succeeds but verify fails
- UART does not prove the DUT actually ran correctly
- DUT may be stuck in an unexpected reset / boot state
- expected meter-observed behavior is missing or incomplete
- verification window may intermittently miss the real signal behavior

Typical signature:
- build and flash are successful
- failure appears in `check` / verify stage
- run may show `FAIL: stage=verify`

### C. Time-related intermittent failures

Examples:
- failure appears only after repeated runs
- success degrades after multiple iterations
- reconnect / reboot recovery is inconsistent
- thermal or long-running effects appear likely

Typical signature:
- first run passes and later runs fail
- iteration number correlates with failure likelihood
- time since last success matters

## 5. Required Observations

Always collect these before proposing a cause:
- iteration number
- time since last success
- whether this was a single suite run or `verify-default repeat`
- ping status to `192.168.4.1`
- TCP status to `192.168.4.1:9000`
- any HTTP / instrument API status available
- Wi-Fi interface state relevant to meter reachability
- route table summary relevant to `192.168.4.1`
- flash result
- exact verify-stage failure location
- whether UART shows the DUT firmware actually ran
- comparison against the most recent successful ESP32-C6 run

Strongly preferred evidence:
- current run id
- evidence path
- verify result path
- instrument doctor output
- instrument describe output
- whether failure happened in iteration 1 or after repeated passes

## 6. Diagnosis Workflow

1. Identify the failure class first.
   - Is it reachability, verify-stage, or time-related intermittent behavior?

2. Record the run context.
   - command used
   - iteration number
   - run id
   - time since last successful ESP32-C6 pass

3. If the failure is a reachability failure, stop and diagnose networking first.
   - check ping to `192.168.4.1`
   - check TCP reachability to port `9000`
   - collect Wi-Fi interface state
   - collect route summary
   - run:
```bash
python3 -m ael instruments doctor --id esp32s3_dev_c_meter
python3 -m ael instruments describe --id esp32s3_dev_c_meter --format text
```

4. If the failure is a verify-stage failure, confirm the earlier stages actually succeeded.
   - did build succeed?
   - did flash succeed?
   - did UART show the firmware ran?
   - did the failure happen before or during instrument signature validation?

5. Compare the failing run to the latest known-good ESP32-C6 run.
   - same meter endpoint?
   - same serial port?
   - same iteration pattern?
   - same stage progression?
   - same connection digest and evidence structure?

6. If the issue appears only after repeated runs, treat repetition as evidence.
   - note first failing iteration
   - note last passing iteration
   - note whether RP2040 and STM32 continued passing
   - if unrelated workers keep passing, bias diagnosis toward ESP32-C6 bench path rather than suite architecture

7. Decide the next action from the evidence, not from the symptom name alone.
   - networking failure -> network / meter diagnostics
   - flash success but no sign of DUT execution -> DUT boot / reset / runtime diagnosis
   - flash and DUT execution confirmed but signature missing -> verify window / measurement / bench signal diagnosis

## 7. Interpretation Guide

Interpretation rules:

- Meter unreachable early:
  - most likely host-side route / Wi-Fi / meter availability issue
  - do not blame the worker architecture first

- Flash succeeds, verify fails:
  - most likely DUT runtime, boot-state, or measurement-window problem
  - confirm whether UART proves the application actually started

- Failure appears only after repeated runs:
  - investigate reconnect / persistence / thermal / recovery behavior
  - record first bad iteration and time since last success

- RP2040 and STM32 keep passing while ESP32-C6 fails:
  - this is evidence against a broad default-verification architecture failure
  - bias toward ESP32-C6-local bench path diagnosis

- Independent worker progression is observed during repeats:
  - do not reclassify the problem as “whole-suite blocking” unless logs show actual shared-resource waiting

## 8. Recommended Output Format

Use this structure when reporting the diagnosis:

- failure classification:
  - `network_meter_reachability`
  - `verify_stage_failure`
  - `time_related_intermittent`
  - `mixed_or_unclear`
- evidence collected:
  - iteration number
  - run id
  - ping / TCP / HTTP status
  - Wi-Fi state
  - route summary
  - flash result
  - UART evidence
  - verify-stage failure location
  - comparison to previous pass
- likely cause:
  - short plain-language statement
- missing evidence:
  - list what is still needed
- next diagnostic action:
  - one concrete next step or command sequence

## 9. Current Known Conclusions

- The ESP32-C6 default verification path is meter-backed and depends on `esp32s3_dev_c_meter`.
- Current evidence supports using worker-level repeats:
  - `python3 -m ael verify-default repeat --limit N`
- Current evidence suggests the remaining intermittent issue is more likely localized to the ESP32-C6 bench path than to the parallel worker architecture itself.
- RP2040 and STM32F103 continuing to pass while ESP32-C6 fails is meaningful evidence, not noise.
- Earlier false shared-probe explanations should not be reused without new evidence.

## 10. Unresolved Questions

- Why does ESP32-C6 sometimes fail at verify stage after successful flash?
- Is the intermittent behavior primarily network / meter recovery related, DUT boot-state related, or measurement-window related?
- Is there any repeat-count threshold where failure probability rises materially?
- Are there DUT-side or meter-side recovery actions that should be automated rather than diagnosed manually?

## 11. Related Files

- [tests/plans/esp32c6_gpio_signature_with_meter.json](/nvme1t/work/codex/ai-embedded-lab/tests/plans/esp32c6_gpio_signature_with_meter.json)
- [configs/default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml)
- [configs/boards/esp32c6_devkit.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/boards/esp32c6_devkit.yaml)
- [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [ael/strategy_resolver.py](/nvme1t/work/codex/ai-embedded-lab/ael/strategy_resolver.py)
- [docs/default_verification.md](/nvme1t/work/codex/ai-embedded-lab/docs/default_verification.md)

## 12. Notes

- This is a reusable troubleshooting workflow, not a timeline.
- Prefer confirming whether the DUT actually ran before changing verification thresholds.
- Prefer collecting comparative evidence from the last successful ESP32-C6 run before proposing code changes.
- When repeated default verification is the goal, prefer `verify-default repeat` over outer shell loops around `verify-default run`.
