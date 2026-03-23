Branch: agent/report-review
Task: report task
Task ID: task_1
Execution Timestamp: 2026-03-22T17:03:33
Execution Mode: offline

## Summary
review summary

## Files Changed
```text
(no file changes detected)
```

## Diff Summary
```text
(no diffstat detected)
```

## Evidence
- run_dir: runs/report-task

## Default Verification Review
- schema_review_status: warnings_present
- structured_coverage: structured=3 legacy=1
- warning_summary: 1 schema warning(s)
- instrument_families: esp32_meter=1
- instrument_health: degraded=1
- failure_boundaries: instrument_service=1
- recovery_hints: recover instrument transport or API availability and retry once=1
- capability_taxonomy_versions: instrument_capabilities/v1=1
- status_health_schema_versions: instrument_status_health/v1=1
- doctor_check_schema_versions: instrument_doctor_checks/v1=1
- capability_taxonomy_enforced: true=1
- status_taxonomy_enforced: true=1
- doctor_checks_enforced: true=1
```text
Default Verification Review
health_status: pass
schema_review_status: warnings_present
structured_coverage: structured=3 legacy=1
warning_summary: 1 schema warning(s)
instrument_families: esp32_meter=1
instrument_health: degraded=1
failure_boundaries: instrument_service=1
recovery_hints: recover instrument transport or API availability and retry once=1
capability_taxonomy_versions: instrument_capabilities/v1=1
status_health_schema_versions: instrument_status_health/v1=1
doctor_check_schema_versions: instrument_doctor_checks/v1=1
capability_taxonomy_enforced: true=1
status_taxonomy_enforced: true=1
doctor_checks_enforced: true=1

```

## Reproduction Instructions
```bash
python3 -m ael submit "review prompt"
```

## Merge Recommendation
merge_ready: no
baseline_readiness_status: needs_attention
merge_advisory: warning-only: baseline readiness needs attention
