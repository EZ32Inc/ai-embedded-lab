# AEL Documentation Index

This index separates current user-facing documentation from historical records.
When answering current-state questions, prefer CLI output and current configs
over older prose.

---

## Current Entry Points

| Document | Purpose |
|---|---|
| [README.md](./README.md) | Short documentation entry point |
| [what_is_ael.md](./what_is_ael.md) | Compact explanation of AEL concepts |
| [DOCS_MAINTENANCE.md](./DOCS_MAINTENANCE.md) | Documentation upkeep, language, naming, and public-safety rules |
| [SECURITY_AND_PUBLIC_REPO.md](./SECURITY_AND_PUBLIC_REPO.md) | Public-repo hygiene for logs, bench details, and sensitive values |
| [DOCS_AUDIT_2026-06-07.md](./DOCS_AUDIT_2026-06-07.md) | Documentation cleanup report and remaining work |
| [ael_cli_reference_v0_1.md](./ael_cli_reference_v0_1.md) | CLI command reference |
| [current_validated_capabilities.md](./current_validated_capabilities.md) | Public validated-capability summary |
| [architecture_map.md](./architecture_map.md) | Current code/module architecture map |
| [agent_answering_guide.md](./agent_answering_guide.md) | How agents should answer repo questions |
| [contributor_rules.md](./contributor_rules.md) | Contributor rules |
| [AI_USAGE_RULES.md](./AI_USAGE_RULES.md) | Agent CLI usage rules |

---

## Current Workflows

| Area | Documents |
|---|---|
| New board bring-up | [new_board_bringup_and_validation_flow.md](./new_board_bringup_and_validation_flow.md), [guides/brownfield_migration_checklist.md](./guides/brownfield_migration_checklist.md) |
| User projects | [specs/user_project_shell_creation_flow_v0_1.md](./specs/user_project_shell_creation_flow_v0_1.md), [specs/user_project_cross_domain_link_convention_v0_1.md](./specs/user_project_cross_domain_link_convention_v0_1.md) |
| Default verification | [default_verification.md](./default_verification.md), [default_verification_execution_model.md](./default_verification_execution_model.md) |
| Instruments | [instruments.md](./instruments.md), [instrument_model_v1.md](./instrument_model_v1.md), [ael_instrument_layer_v1_0.md](./ael_instrument_layer_v1_0.md) |
| Recovery and degraded instruments | [degraded_instrument_policy.md](./degraded_instrument_policy.md), [failure_taxonomy_v0_1.md](./failure_taxonomy_v0_1.md) |

---

## Directories

| Directory | Status | Use |
|---|---|---|
| [boards/](./boards/) | Current + historical | Board notes and board-specific closeouts; start with [boards/README.md](./boards/README.md) |
| [guides/](./guides/) | Current | Practical user workflows |
| [reports/](./reports/) | Historical evidence | Validation closeouts and investigations; start with [reports/README.md](./reports/README.md) |
| [roadmap/](./roadmap/) | Mixed | Planning documents; prefer newest files |
| [specs/](./specs/) | Mixed | Versioned specs, drafts, and policy documents; start with [specs/README.md](./specs/README.md) |
| [skills/](./skills/) | Current + historical | Reusable AI-agent workflow knowledge |
| [tutorials/](./tutorials/) | Current + historical | Long-form walkthroughs |
| [archive/](./archive/) | Historical | Archived reference material |
| [books/](./books/) | Non-operational | Essay/book material, not project instructions |
| [reports/raw/](./reports/raw/) | Historical/raw | Large raw logs; not public-facing guidance |

---

## Historical Material Policy

Historical reports and archived docs are useful evidence, but they should not be
used as the first source for current behavior. Use this order:

1. CLI output
2. current configs, packs, manifests, and tests
3. implementation code
4. current docs
5. reports and archive

Docs with `Draft`, `Closeout`, `Report`, or a date in the filename may describe
a point-in-time result rather than current behavior.
