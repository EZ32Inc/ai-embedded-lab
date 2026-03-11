# Compatibility Deprecation Review

## Purpose

Provide a bounded workflow for deciding whether a remaining compatibility seam should be kept, retired next, or deferred.

## When To Use

Use this when:
- Phase 2 asks for a compatibility checkpoint
- a legacy field/function/name still exists and someone asks whether it should remain
- the repo is at risk of doing cleanup for its own sake instead of for operator or architecture value

## Review Order

1. Is it user-visible now?
2. Is it part of the active runtime/report/archive contract?
3. Is it only an explicit compatibility object?
4. Is it mainly an internal helper seam?
5. Would removal create broad churn without meaningful clarity gain?

## Decision Rule

Prefer:
- retire next, if it is user-visible and still looks primary
- keep for now, if it is explicit compatibility and low-risk
- defer, if it is mostly internal and removal would create broad churn

## Recommended Output

For each seam, classify:
- `keep for now`
- `retire next`
- `defer`

And explain briefly:
- user-visible impact
- contract impact
- churn risk

## Current AEL Bias

Current Phase 2 bias should be:
- user-facing clarity first
- compatibility objects explicit
- internal renames only when they unlock real value

## Related Files

- [control_instrument_compatibility.md](/nvme1t/work/codex/ai-embedded-lab/docs/control_instrument_compatibility.md)
- [active_doc_cleanup_workflow.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/active_doc_cleanup_workflow.md)
- [ael_phase2_roadmap_2026-03-11.md](/nvme1t/work/codex/ai-embedded-lab/docs/roadmap/ael_phase2_roadmap_2026-03-11.md)
