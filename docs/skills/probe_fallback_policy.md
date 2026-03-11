# Probe Fallback Policy

## 1. Purpose

This document explains how AEL currently handles explicit probe binding, legacy probe fallback, and no-implicit-probe paths.

Its goal is to prevent incorrect bench modeling caused by hidden or inherited probe assumptions.

## 2. Scope

Use this document when:
- explaining why a task did or did not get a probe
- reviewing board configuration or default verification behavior
- diagnosing false resource sharing caused by legacy assumptions

This document is especially relevant for:
- default verification
- stage explanation
- probe binding review

## 3. Background

Some AEL paths use a real probe-backed execution model.
Some use a meter-backed or otherwise non-probe path.

Historically, legacy fallback behavior could cause a board to inherit a shared probe binding even when that did not reflect the real bench model.

That is dangerous because it can:
- serialize unrelated work
- misstate the selected setup in explanations
- confuse architecture diagnosis

## 4. Failure / Issue Classes

### A. Explicit probe binding

Meaning:
- the board or step directly selects a probe instance or probe config

Expected behavior:
- use that binding
- reflect it in execution and explanation

### B. Legacy implicit fallback

Meaning:
- no explicit probe was chosen, so an older default binding is inherited

Risk:
- may not reflect the real bench model
- may create false shared-resource assumptions

### C. No implicit probe binding

Meaning:
- the path should proceed without assigning a probe unless one is explicitly configured

Use case:
- meter-backed paths that should not silently attach a shared debug probe

## 5. Required Observations

Before explaining probe selection, collect:
- board id
- test path
- explicit `instrument_instance` if present
- explicit `probe` config if present
- whether the board allows legacy fallback
- selected probe shown by stage explanation
- task resource keys if resource sharing is being discussed

## 6. Diagnosis Workflow

1. Check for an explicit probe instance on the step or board.

2. If none exists, check for an explicit probe config path.

3. If neither exists, determine whether legacy fallback is allowed for that board/path.

4. If legacy fallback is disabled, treat the path as no-implicit-probe.

5. Confirm that execution behavior and stage explanation agree with the selected model.

6. If a resource-sharing claim depends on probe choice, verify that the probe binding is real and not inherited accidentally.

## 7. Interpretation Guide

- Explicit probe binding:
  - strongest and preferred form
  - easiest to reason about

- Legacy fallback:
  - compatibility behavior
  - should be treated carefully
  - acceptable only when it still matches real bench intent

- No implicit probe binding:
  - correct for some non-probe paths
  - absence of a probe is intentional, not a missing-data bug

## 8. Recommended Output Format

When explaining probe selection, report:
- binding mode:
  - `explicit_instance`
  - `explicit_probe_config`
  - `legacy_fallback`
  - `no_implicit_probe`
- selected probe identity, if any
- whether the result matches the real bench model
- whether any shared-resource conclusion depends on that probe choice

## 9. Current Known Conclusions

- Hidden legacy fallback can create false shared-resource serialization and false explanations.
- Some board/test paths should disable legacy implicit fallback.
- Execution and stage explanation should reflect the real bench model, not historical convenience defaults.
- Meter-backed ESP32-C6 default verification should not be explained as sharing an unrelated legacy probe unless explicit configuration says so.

## 10. Unresolved Questions

- Which remaining boards should explicitly disable legacy fallback?
- Should the probe/instrument naming split be further unified in code and docs?

## 11. Related Files

- [ael/config_resolver.py](/nvme1t/work/codex/ai-embedded-lab/ael/config_resolver.py)
- [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [ael/stage_explain.py](/nvme1t/work/codex/ai-embedded-lab/ael/stage_explain.py)
- [tests/test_probe_binding.py](/nvme1t/work/codex/ai-embedded-lab/tests/test_probe_binding.py)
- [configs/boards/esp32c6_devkit.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/boards/esp32c6_devkit.yaml)

## 12. Notes

- Prefer explicitness over inherited defaults when bench correctness matters.
- Do not treat a probe fallback artifact as proof of a real bench dependency.
