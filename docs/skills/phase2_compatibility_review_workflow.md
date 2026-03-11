# Phase 2 Compatibility Review Workflow

## Purpose

Provide a reusable review workflow for checking whether remaining compatibility surfaces in AEL are still justified.

## When To Use

Use this when:
- a Phase 2 cleanup batch is being planned
- user-visible wording still mixes canonical and legacy concepts
- someone asks whether a compatibility field should be retired

## Primary Review Order

1. Active user-facing CLI/help
2. Active runtime/report/archive outputs
3. Active workflow/docs/examples
4. Older examples/specs
5. Internal helper names and adapter parameters

Retire from the top of the list first.

## Canonical Rule

Prefer:
- `control_instrument*`
- `selected_dut`
- `selected_board_profile`
- `selected_bench_resources`

Treat older `probe*`, flat board aliases, and similar fields as compatibility only.

## Questions To Ask

1. Can a normal user still see this legacy term?
2. If so, does it look primary or explicitly legacy?
3. Is the remaining compatibility serving a real consumer, or just inertia?
4. Would removal create broad churn in internal code that is not user-visible?

## Recommended Outcome Format

For each surface:
- `keep for now`
- `demote to compatibility`
- `retire next`
- `defer because internal churn exceeds current value`

## Related Files

- [control_instrument_compatibility.md](/nvme1t/work/codex/ai-embedded-lab/docs/control_instrument_compatibility.md)
- [ael_phase2_roadmap_2026-03-11.md](/nvme1t/work/codex/ai-embedded-lab/docs/roadmap/ael_phase2_roadmap_2026-03-11.md)
