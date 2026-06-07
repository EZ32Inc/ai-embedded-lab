# DUT Migration Implementation Guide

**Status:** Historical migration note
**Original date:** 2026-03-21
**Last reviewed:** 2026-06-07

This file used to be a step-by-step implementation guide for introducing the
`ael/dut/` model layer. That work has already been implemented in the current
codebase.

Current DUT model files:

- `ael/dut/model.py`
- `ael/dut/loader.py`
- `ael/dut/registry.py`
- `ael/dut/interfaces/`

Related design documents:

- [dut_standardization_spec_v0_1.md](./dut_standardization_spec_v0_1.md)
- [dut_standardization_migration_plan_v0_1.md](./dut_standardization_migration_plan_v0_1.md)

## Current Guidance

Do not follow the original migration steps literally. They described a planned
state from March 2026 and included assumptions that are no longer true, such as
`ael/dut/` not existing.

For current work:

1. Inspect the implementation under `ael/dut/`.
2. Verify behavior through current inventory and board commands.
3. Update design docs only after checking live code and tests.
4. Keep compatibility adapters simple and runnable.

Useful checks:

```bash
python3 -m ael inventory list
python3 -m ael board --help
python3 -m pytest tests -k dut
```

## Remaining Migration Themes

The completed implementation does not mean DUT standardization is finished.
The remaining work should be treated as normal follow-up, not as a bootstrap
migration:

- reduce direct raw-dict access where structured DUT interfaces are available
- keep board identity board-first rather than MCU-first
- preserve compatibility with existing manifests and board YAML files
- add tests before changing shared runtime behavior
- keep public docs aligned with current CLI behavior

## Historical Note

The original version of this document contained detailed code snippets for
creating `ael/dut/__init__.py`, `model.py`, `loader.py`, and `registry.py`.
Those snippets have been removed because they are superseded by the current
implementation and could mislead contributors into recreating already existing
files.
