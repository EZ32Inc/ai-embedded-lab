# AEL Documentation

AEL (AI Embedded Lab) is an AI-assisted hardware validation system for
embedded boards. It keeps board definitions, firmware targets, test plans,
bench instruments, and run evidence in one repository so an AI agent can help
plan, build, flash, observe, verify, and record hardware work.

Use this file as the short public entry point. For the full documentation map,
see [DOCS_INDEX.md](./DOCS_INDEX.md).

---

## Start Here

| Need | Document |
|---|---|
| Short project explanation | [what_is_ael.md](./what_is_ael.md) |
| CLI command reference | [ael_cli_reference_v0_1.md](./ael_cli_reference_v0_1.md) |
| Current architecture map | [architecture_map.md](./architecture_map.md) |
| Current validated capabilities | [current_validated_capabilities.md](./current_validated_capabilities.md) |
| Contributor rules | [contributor_rules.md](./contributor_rules.md) |
| AI agent usage rules | [AI_USAGE_RULES.md](./AI_USAGE_RULES.md) |

---

## Current Public Baseline

The public `master` branch is anchored by validated golden-suite work across
several MCU families. The latest public milestones include:

- **CH32V305RBT6**: golden suite complete, `25/25 PASS`
  ([report](../reports/ch32v305xxx_golden_suite_report.md))
- **CH32V203C8T6**: golden suite complete, `23/23 PASS`
  ([closeout](./reports/ch32v203_nanoch32v203_golden_suite_closeout_2026-04-12.md))
- **nRF52840 nice!nano**: first Nordic/Zephyr-native golden suite, `15/15 PASS`
  ([closeout](./reports/nrf52840_nicenano_golden_suite_closeout_2026-04-12.md))
- **CH32V003F4U6**: first WCH RISC-V validation path, currently `13/13` in the
  public golden set after the unsafe sleep test was removed
  ([closeout](./reports/ch32v003_golden_suite_closeout_2026-04-06.md))

For live truth, prefer the CLI over historical prose:

```bash
python3 -m ael inventory list --format text
python3 -m ael project list
python3 -m ael verify-default state
```

---

## Common Commands

```bash
python3 -m ael status
python3 -m ael inventory list --format text
python3 -m ael project list
python3 -m ael board state <board_id> --format text
python3 -m ael run --board <board_id> --test <test_id>
python3 -m ael pack --board <board_id> --pack packs/<pack>.json
```

Supported top-level commands on the current public branch:

```text
run, doctor, pack, instruments, dut, verify-default, inventory, connection,
explain-stage, workflow-archive, hw-check, la-check, status, board, project,
invoke
```

---

## Documentation Layout

| Directory | Purpose |
|---|---|
| [boards/](./boards/) | Board-specific notes and current board summaries |
| [guides/](./guides/) | User-facing workflows and practical procedures |
| [reports/](./reports/) | Validation closeouts, investigations, and historical run records |
| [roadmap/](./roadmap/) | Current and historical planning documents |
| [specs/](./specs/) | Versioned design specs and policy documents |
| [skills/](./skills/) | Reusable AI-agent workflow knowledge |
| [tutorials/](./tutorials/) | Longer walkthroughs with images |
| [archive/](./archive/) | Historical reference material |

The repository also contains older design documents in the root of `docs/`.
When answering current-state questions, use this source order:

1. CLI output
2. current configs, manifests, packs, and test plans
3. implementation code
4. current docs
5. historical reports and archived docs

---

## Important Boundary

"Supported" means the repository contains a validated or candidate path. It
does not prove that a user's specific board is connected, powered, wired
correctly, or ready to run. AEL always needs the user's real setup facts before
running hardware tests.
