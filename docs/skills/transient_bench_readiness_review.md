# Transient Bench Readiness Review

## Purpose

Review whether an early instrument failure is likely a true unreachable condition or a short bench-readiness transient.

## Scope

Use this when:
- a meter-backed worker fails early with `network_meter_reachability`
- manual ping or TCP checks show the instrument becomes reachable shortly afterward
- a user wants to know whether AEL should change policy or simply record the bench behavior

## Required Observations

Collect:
- direct live run result, not only sandboxed or restricted execution output
- `failure_class`
- `instrument_condition`
- `retry_summary`
- raw `ping`, `tcp`, and `api` observations if present
- manual follow-up checks if available

## Interpretation Guide

Typical cases:

- first-attempt latency spike, then instrument becomes reachable:
  - likely transient bench readiness
  - bounded timeout tolerance may be justified

- repeated direct live failures with ping/tcp/api all down:
  - likely true bench-side unreachable state
  - do not hide it behind aggressive retries

- restricted execution context shows `Operation not permitted`:
  - not valid bench evidence
  - do not treat that as meter instability

## Recommended Action

Use bounded policy only:
- allow a slightly larger early guard window when direct bench evidence justifies it
- consider one short retry only if repeated live evidence shows the path often becomes healthy immediately after startup
- avoid broad recovery flows unless hardware reset/recovery is real and supported

## Current Known Conclusion

In the current repo, transient readiness tolerance is acceptable as a small run-path policy adjustment.
It should remain bounded and evidence-driven.

## Related Files

- [degraded_instrument_policy.md](/nvme1t/work/codex/ai-embedded-lab/docs/degraded_instrument_policy.md)
- [degraded_instrument_policy_usage.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/degraded_instrument_policy_usage.md)
- [provision.py](/nvme1t/work/codex/ai-embedded-lab/ael/instruments/provision.py)
- [default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
