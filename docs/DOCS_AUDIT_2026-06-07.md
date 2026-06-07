# Documentation Audit Report

**Date:** 2026-06-07
**Branch:** `master`
**Scope:** `docs/`

This report records the documentation cleanup performed on 2026-06-07 and the
remaining work needed to keep AEL documentation public-ready.

## Summary

The documentation tree has been reorganized around current public entry points,
section indexes, and an explicit maintenance policy.

Current state after cleanup and follow-up public-safety work:

- `docs/` contains 598 files.
- Public entry points are English-first and linked from
  [DOCS_INDEX.md](./DOCS_INDEX.md).
- `docs/obsolete/` has been removed.
- Large raw development logs have been removed from the public docs tree.
- High-priority root-level mixed-language docs have been translated or replaced
  with English versions.

## Commits Created

| Commit | Purpose |
|---|---|
| `60486ef` | Refreshed public documentation entry points |
| `10168fd` | Added section indexes and documentation maintenance policy |
| `a05a001` | Removed obsolete docs and initially isolated raw logs |
| `2255649` | Cleaned up high-priority public docs language |
| `4d29554` | Added this documentation audit report |
| `08bbe61` | Removed raw logs from the public docs tree |
| `e319b43` | Added public-repo security guide |
| `18d902d` | Refreshed skills and instruments entry points |

## Deleted Documents

The following documents were removed because they were already marked obsolete,
described superseded CLI/agent/instrument behavior, or had no remaining value as
current public documentation:

| Deleted file | Reason |
|---|---|
| `docs/obsolete/ael_agent_v0_4_implementation_spec.md` | Superseded agent implementation draft |
| `docs/obsolete/ael_architecture_v0_1.md` | Superseded architecture draft |
| `docs/obsolete/ael_architecture_v0_1_diagram.md` | Superseded architecture diagram text |
| `docs/obsolete/ael_instrument_protocol_v0_1.md` | Superseded instrument protocol draft |
| `docs/obsolete/agent_v0_5_usage.md` | Superseded agent usage note |
| `docs/obsolete/aip-0.1.json` | Obsolete protocol artifact |
| `docs/obsolete/download_mode_role_backend_cleanup.md` | Completed cleanup note |
| `docs/obsolete/local_instrument_interface_refactor_plan_v0_1.md` | Superseded refactor plan |
| `docs/obsolete/night_tasks_agent_v0_3.md` | Superseded night-task agent draft |
| `docs/obsolete/night_tasks_agent_v0_4_notes.md` | Superseded night-task agent notes |
| `docs/obsolete/phase1_cli_cleanup.md` | Completed phase-1 cleanup note |
| `docs/obsolete/serial_role_backend_cleanup.md` | Completed cleanup note |
| `docs/obsolete/uart_role_backend_cleanup.md` | Completed cleanup note |

## Removed Raw Logs

The following raw logs were first moved out of the main reports list, then
removed from the public docs tree because they are large, historical, and may
contain bench-local details:

| Removed file | Reason |
|---|---|
| `docs/reports/raw/ael_daplink_stm32f103rct6_dev_whole_log-2026-04-01.txt` | Raw interactive transcript with local bench details |
| `docs/reports/raw/ael_esp32jtag_stm32f103c6t6_dev_whole_log-2026-04-01.txt` | Raw interactive transcript with local bench details |

## Retained Documents

The following document groups should remain, with different levels of trust:

| Group | Status | Notes |
|---|---|---|
| `docs/README.md`, `docs/DOCS_INDEX.md` | Current | Primary public entry points |
| `docs/DOCS_MAINTENANCE.md` | Current | Documentation rules and public-repo safety checks |
| `docs/ael_cli_reference_v0_1.md` | Current | Refreshed against CLI help |
| `docs/current_validated_capabilities.md` | Current summary | Public-safe validated-capability overview |
| `docs/architecture_map.md` | Current summary | Current code/module map |
| `docs/boards/` | Current + historical | Board fact sheets and board closeouts |
| `docs/guides/` | Current | Practical user workflows |
| `docs/reports/` | Historical evidence | Validation reports and investigations |
| `docs/specs/` | Mixed | Versioned specs, drafts, policies, and checkpoints |
| `docs/skills/` | Current + historical | Reusable AI-agent workflow knowledge |
| `docs/archive/` | Historical | Reference only |
| `docs/books/` | Non-operational | Essay/book material, not project instructions |

## Documents Updated Now

| Document | Change |
|---|---|
| `docs/README.md` | Rewritten as a concise current docs entry point |
| `docs/DOCS_INDEX.md` | Added current entry points, directory status, and raw-log policy |
| `docs/DOCS_MAINTENANCE.md` | Added documentation maintenance and public-safety policy |
| `docs/SECURITY_AND_PUBLIC_REPO.md` | Added public-repo hygiene rules for logs and bench details |
| `docs/ael_cli_reference_v0_1.md` | Refreshed from current CLI shape |
| `docs/current_validated_capabilities.md` | Replaced stale capability claims with public-safe baseline |
| `docs/architecture_map.md` | Updated current module and CLI summary |
| `docs/boards/README.md` | Added board directory index |
| `docs/reports/README.md` | Added report-use policy and raw-log handling |
| `docs/specs/README.md` | Added spec directory index and cleanup rules |
| `docs/skills/README.md` | Added active/historical skill policy and public-safety rules |
| `docs/instruments.md` | Rewritten as a public-safe current instrument entry point |
| `docs/instruments/usb_uart_bridge_daemon_v0_1.md` | Replaced absolute links and local examples with relative links/placeholders |
| `docs/AELToDoList.md` | Translated and normalized as English task list |
| `docs/ael_vs_vibe_coding.md` | Translated and rewritten in English |
| `docs/ael_paradigm_shift.md` | Removed mixed-language heading and normalized metadata |
| `docs/dut_migration_implementation_guide.md` | Replaced obsolete implementation steps with historical status note |

## Needs Update

These files still have value but should be checked against current code before
being treated as active guidance:

| Document | Required update |
|---|---|
| `docs/skills/README.md` | Separate active reusable skills from historical captures |
| `docs/roadmap/ael_next_things_to_do_v0_21.md` | Reconcile with current `AELToDoList.md` and current code |
| `docs/ael_architecture.md` and related architecture roots | Consolidate with `architecture_map.md`; mark older files historical |
| `docs/instrument_architecture.md`, `docs/instrument_model.md`, `docs/instrument_model_v1.md` | Consolidate into one current instrument model entry |
| `docs/default_verification*.md` | Confirm current verification contract and archive older closeouts |
| `docs/dut_standardization_*` | Mark implemented portions and remaining migration themes |
| `docs/reports/*.md` | Add short summaries where reports still contain mixed-language notes |
| `docs/specs/generated_example_*` and `docs/specs/example_*` | Decide whether to archive as planning history |

## Language Cleanup Remaining

The high-priority public root docs have been cleaned, but Chinese or
mixed-language content remains in historical and lower-priority files.

Residual groups:

- architecture and scheduling drafts:
  `ael_architecture_gaps_2026-03-20.md`,
  `ael_execution_parallel_scheduling_architecture_2026-03-20.md`
- methodology and plan notes under `docs/methodology/` and `docs/plans/`
- dated validation reports under `docs/reports/`
- selected skills under `docs/skills/`
- selected specs and memos under `docs/specs/`
- non-operational book material under `docs/books/`

Recommended handling:

1. Translate or replace active agent/contributor guidance first.
2. Summarize historical reports in English rather than translating full logs.
3. Keep raw logs outside the public repo unless explicitly sanitized.
4. Archive or delete non-operational Chinese essays if they are not useful for
   the public repo.

## Suggested New Documents

| Suggested document | Purpose | Priority |
|---|---|---|
| `docs/CONTRIBUTING.md` or root `CONTRIBUTING.md` | Public contributor workflow, commit discipline, validation expectations | High |
| `docs/SECURITY_AND_PUBLIC_REPO.md` | Explicit public-repo hygiene checklist for logs, IPs, paths, and credentials | High |
| `docs/quickstart.md` | Minimal first-run path for a new user | High |
| `docs/instruments/README.md` | Current instrument model and supported control instruments | Medium |
| `docs/skills/README.md` refresh | Active skill index separated from historical captures | Medium |
| `docs/archive/README.md` | Archive policy and historical-use warning | Medium |

## Structure Recommendations

Priority order:

1. Keep `docs/README.md`, `docs/DOCS_INDEX.md`, and `docs/ael_cli_reference_v0_1.md`
   accurate whenever CLI behavior changes.
2. Treat `docs/reports/` as evidence, not current instructions.
3. Promote only current specs into `DOCS_INDEX.md`; leave older specs as
   historical until reviewed.
4. Keep raw logs and full transcripts outside public branches unless sanitized.
5. Keep public documentation English-first.
6. Avoid new filenames with spaces, punctuation-heavy names, or non-ASCII
   characters.
7. Consolidate duplicate root architecture and instrument docs after the next
   implementation milestone.

## Validation Performed

- `git diff --check`
- `python3 -m ael --help`
- `python3 -m ael board --help`
- `python3 -m ael inventory list`
- Chinese-character scan for high-priority cleaned files
- Public-safety scan for the high-priority cleaned files

## Residual Risk

This cleanup improved the public documentation surface, but it did not fully
sanitize every historical report. Before pushing a public release, review
remaining historical files for private IP addresses, absolute local paths,
serial numbers, credentials, and bench-specific details.
