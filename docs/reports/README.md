# Reports

This directory contains dated validation reports, closeouts, and investigation
records. Reports are historical evidence, not the first source for current CLI
or architecture behavior.

For current status, start with:

- [../current_validated_capabilities.md](../current_validated_capabilities.md)
- [../DOCS_INDEX.md](../DOCS_INDEX.md)
- current packs, manifests, configs, and tests in the repository

## Current Use

Use reports to answer:

- which board/test combinations were validated at a specific point in time
- what failed during a bring-up or investigation
- what evidence supported a milestone or closeout
- which assumptions should be revalidated before expanding a pack

Do not use reports as the only source for:

- current CLI syntax
- current module boundaries
- current hardware inventory
- current pass/fail state after code or hardware changes

## High-Value Report Groups

| Group | Examples |
|---|---|
| Golden-suite closeouts | `*_golden_suite_closeout_*.md` |
| STM32 validation | `stm32*_closeout_*.md`, `stm32*_debug_*.md` |
| ESP32 Rule-B validation | `esp32*_rule_b_closeout_*.md` |
| CH32V validation | `ch32v*_golden_suite_closeout_*.md` |
| Default verification | `default_verification_run_*.md` |

## Raw Logs

Large raw logs are not kept on the public `master` branch by default. If a raw
log contains reusable evidence, summarize it as a dated report and keep the full
transcript outside the public repo unless it has been explicitly sanitized.

Before publishing raw logs, check for local paths, private IP addresses,
serial numbers, tokens, and bench-specific environment details.
