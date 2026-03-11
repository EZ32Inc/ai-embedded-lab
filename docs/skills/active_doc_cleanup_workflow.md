# Active Doc Cleanup Workflow

## Purpose

Provide a bounded workflow for cleaning active docs/examples without drifting into a broad historical rewrite.

## When To Use

Use this when:
- Phase 2 calls for visible compatibility cleanup
- current docs still expose older architecture wording
- the goal is user-facing clarity, not repo-wide terminology purity

## Priority Order

1. Active runtime/how-to docs
2. Active roadmap and compatibility notes
3. Reusable workflow/skills docs
4. Trace/review/reference docs that users still read
5. Historical specs/reports only if they are actively misleading

## Cleanup Rules

1. Prefer canonical current wording first.
2. Keep explicit legacy wording only when the topic is compatibility or history.
3. Do not rewrite stable historical documents unless they are misleading current work.
4. If a term is still used internally for compatibility, note that instead of hiding it.

## Typical Targets

- `board/probe/test` -> `board/control-instrument/test`
- `probe or instrument` -> `control instrument or instrument`
- runtime/output descriptions that ignore:
  - `selected_dut`
  - `selected_board_profile`
  - `selected_bench_resources`

## Done Criteria

- active user-facing docs read consistently with the current canonical model
- remaining legacy wording is either explicit compatibility or clearly historical

## Related Files

- [control_instrument_compatibility.md](/nvme1t/work/codex/ai-embedded-lab/docs/control_instrument_compatibility.md)
- [ael_phase2_roadmap_2026-03-11.md](/nvme1t/work/codex/ai-embedded-lab/docs/roadmap/ael_phase2_roadmap_2026-03-11.md)
