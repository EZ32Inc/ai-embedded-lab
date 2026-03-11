# Degraded Instrument Handling

## Purpose

This document explains how to interpret AEL behavior when an external instrument is present but unstable, partially reachable, or intermittently unusable.

Its goal is to help separate:
- AEL execution-model behavior
- bench/resource behavior
- instrument-specific instability

## Scope

This guidance applies when AEL depends on a real bench instrument and that instrument behaves badly enough to affect readiness checks or verify-stage execution.

Examples:
- a meter AP is reachable only intermittently
- TCP connects but the instrument API does not answer
- an instrument answers readiness checks but later verify fails through the instrument path

## Background

AEL now treats instruments as first-class runtime resources.

This means a “bad instrument” is not only a device problem.
It is also a test of whether AEL:
- classifies failure correctly
- preserves useful evidence
- keeps unrelated workers running
- avoids misreporting bench faults as execution-architecture faults

## Failure / Issue Classes

Current useful categories include:

- `instrument_unreachable`
  - no usable network path to the instrument
- `instrument_transport_unavailable`
  - basic reachability exists, but the required transport path is not usable
- `instrument_api_unavailable`
  - transport accepts connection, but the instrument service/API is not responding correctly
- `instrument_ready_with_network_warning`
  - instrument path is usable, but there is still a warning signal such as ICMP failure
- `instrument_verify_failed`
  - the instrument path was reachable enough to run, but verification later failed through that path

These are operator-facing interpretations, not claims about the physical root cause.

## Required Observations

When diagnosing a degraded instrument case, collect:

- `failure_class`
- `instrument_condition`
- `verify_substage`, if any
- `resource_keys`
- `resource_summary`
- network observations such as `ping`, `tcp`, and `api`
- connection setup / connection digest
- whether unrelated workers continued independently

## Diagnosis Workflow

1. Check whether the failure happened before run or during verify.
2. Read `instrument_condition` first.
3. Read `failure_class` second.
4. Confirm the bound resource identity from `selected_bench_resources`.
5. Confirm whether other workers progressed normally.
6. Treat the issue as bench/instrument-side unless evidence points to an AEL execution-model defect.

## Interpretation Guide

- `instrument_unreachable`:
  - the bench path to the instrument is not usable
  - do not blame worker scheduling or resource locking first

- `instrument_transport_unavailable`:
  - the instrument host is partially reachable but the required transport path is broken
  - usually still bench/network-side

- `instrument_api_unavailable`:
  - the instrument service is degraded, hung, or not responding as expected
  - this is a strong “bad instrument” case

- `instrument_verify_failed`:
  - the instrument was reachable enough to start, but later verification through the instrument failed
  - inspect verify evidence before concluding whether the problem is DUT-side or instrument-side

- unrelated workers still passing:
  - strong evidence that the core execution model is behaving correctly under degraded bench conditions

## Recommended Output Format

When explaining a degraded instrument failure, report:

- task name
- `failure_class`
- `instrument_condition`
- `verify_substage`, if present
- exact error summary
- compact observations
- whether unrelated workers continued

## Current Known Conclusions

- AEL should treat a bad instrument as a bench/resource condition first, not as proof of an execution-model defect.
- Worker independence is an important validation signal in these cases.
- The instrument condition should be visible directly in results and summaries, not only buried in raw evidence.

## Unresolved Questions

- whether future instruments need a broader condition taxonomy than the current meter-focused cases
- how much automatic retry or recovery policy should be attached to degraded instrument states
- whether additional timing/history context is needed for intermittent API failures

## Related Files

- [ael/instruments/provision.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/provision.py)
- [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [ael/verification_model.py](/nvme1t/work/codex/ai-embedded-lab/ael/verification_model.py)
- [docs/bench_resource_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/bench_resource_model.md)

## Notes

- Do not overfit this workflow to ESP32-C6 only.
- The same reasoning should apply to future unstable instruments and degraded bench endpoints.
