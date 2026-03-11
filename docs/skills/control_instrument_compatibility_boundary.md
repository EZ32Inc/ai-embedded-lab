# Control Instrument Compatibility Boundary

## Purpose

Explain what remains intentionally compatible in the old `probe*` surface and what should no longer be treated as primary.

## Scope

Use this when reviewing:
- user-facing docs/examples
- runtime/archive payload expectations
- deprecation readiness for legacy control-instrument terminology

## Canonical Rule

Treat these as primary:
- `control_instrument`
- `control_instrument_instance`
- `control_instrument_selection`

Treat `probe*` only as explicit compatibility.

## Keep For Now

- compatibility objects in runtime/archive payloads
- legacy raw config names such as `probe_config`
- selected internal wrappers where immediate removal would create broad churn

## Prefer To Retire Next

- remaining user-visible doc/examples that still present `probe` as current primary wording
- remaining help text that mentions `--probe` without an explicit legacy note

## Interpretation Guide

If both canonical and legacy forms exist:
- code and docs should read canonical first
- legacy should only support older callers or older stored payloads

## Related Files

- [control_instrument_compatibility.md](/nvme1t/work/codex/ai-embedded-lab/docs/control_instrument_compatibility.md)
- [probe_fallback_policy.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/probe_fallback_policy.md)
