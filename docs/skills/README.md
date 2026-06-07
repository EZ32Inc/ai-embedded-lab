# AEL Skills

This directory stores reusable engineering knowledge extracted from real AEL
development, validation, and bench work.

Skill docs are not raw logs. They should capture what should be reused next
time: diagnosis workflows, known failure classes, validation patterns, and
operator guidance.

## How To Use This Directory

Use this order:

1. Start with current public docs:
   - [../README.md](../README.md)
   - [../DOCS_INDEX.md](../DOCS_INDEX.md)
   - [../ael_cli_reference_v0_1.md](../ael_cli_reference_v0_1.md)
2. Use active skills for recurring workflows and troubleshooting.
3. Treat dated board-specific skills as historical captures unless they match
   the current board, instrument, and code path.
4. Verify current commands with CLI help before running hardware actions.

## Active Skill Groups

| Area | Representative files |
|---|---|
| Agent/repo orientation | `ael_orientation_skill.md`, `ael_repo_answering_skill.md`, `user_project_answering_skill.md` |
| Documentation cleanup | `active_doc_cleanup_workflow.md` |
| New board and pack work | `new_board_bringup_skill.md`, `new_pack_closeout_and_skill_capture.md`, `capability_expansion_skill_v0_1.md` |
| Default verification | `default_verification_repeat_mode.md`, `default_verification_repeat_skill.md`, `default_verification_single_run_triage.md` |
| Degraded instruments and bench drift | `degraded_instrument_handling.md`, `bench_drift_vs_degraded_instrument.md`, `bench_resource_drift_interpretation.md` |
| Resource locking and concurrency | `worker_resource_locking.md`, `probe_fallback_policy.md` |
| User projects | `user_project_creation_skill.md`, `connection_contract_retrieval.md` |
| Validation summaries | `validation_summary_emission_skill.md`, `last_known_good_extraction_skill.md` |

## Historical Capture Groups

Many files are dated board-specific captures. They remain useful evidence but
should not be treated as current instructions without checking the code and
current configs.

Examples:

- `rp2040_s3jtag_*_2026-03-26.md`
- `stm32f030c8t6_*_2026-04-03.md`
- `stm32f103*_2026-03-28.md`
- `stm32f401*_2026-03-28.md`
- `stm32f401ce_*_2026-04-05.md`

These files are best used to recover known patterns:

- what failed before
- which evidence was collected
- which mitigation worked
- which validation closeout was required

## What A Good Skill Contains

A reusable skill should usually include:

- purpose
- scope
- prerequisites
- required observations
- diagnosis workflow
- interpretation guide
- recommended output format
- known conclusions
- unresolved questions
- related files

Keep skills concise and actionable. Link to reports for detailed evidence
instead of copying raw logs into the skill.

## What Does Not Belong Here

Do not add:

- raw session logs
- unsanitized terminal transcripts
- private bench IP addresses or serial numbers
- one-off brainstorming notes
- generic essays that do not change engineering behavior

If a raw session produced reusable knowledge, summarize it as a skill and store
the raw transcript outside public branches unless it has been sanitized.

## Naming Rules

Use lowercase snake_case filenames for new skills.

Good examples:

- `esp32c6_intermittent_bench_failure.md`
- `default_verification_repeat_mode.md`
- `probe_fallback_policy.md`
- `worker_resource_locking.md`

Avoid vague names such as:

- `notes_1.md`
- `new_workflow.md`
- `thoughts.md`

## Maintenance

When a skill becomes stale:

1. Update it if the workflow is still active.
2. Mark it historical if it is useful only as evidence.
3. Remove it if it duplicates a better current skill and has no unique value.

Before committing, run the public-repo checks in
[../SECURITY_AND_PUBLIC_REPO.md](../SECURITY_AND_PUBLIC_REPO.md).
