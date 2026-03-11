# AEL Assets: Golden vs User

## Overview
AEL separates DUT assets into two buckets:
- `assets_golden/`: verified reference DUTs shipped with AEL.
- `assets_user/`: user-created DUTs that are not shipped or may be experimental.

Golden assets act as templates and known-good references. User assets are derived from golden or created from scratch and can be promoted after verification.

## How AEL Chooses a Golden Reference
When you request a DUT by `mcu`, `family`, or `tags`, AEL uses a simple scoring rule:
1) Exact `mcu` match
2) Same `family`
3) Tag overlap

This provides a best-effort reference when a user DUT is missing, and helps bootstrap new boards.

## Promotion Workflow
1) Create a user DUT from a golden reference:
   - `python3 -m ael dut create --from-golden <golden_id> --to <user_id>`
2) Adjust the user DUT manifest, tests, wiring notes, and any project files.
3) Verify on a bench and record verification metadata in `manifest.yaml`.
4) Promote:
   - `python3 -m ael dut promote --id <user_id> --as <golden_id>`

## Promotion Checklist
- `manifest.yaml` exists and passes schema validation
- at least one deterministic test/pack included
- passes on a defined bench (or has `verified_on` info recorded)
- includes `docs.md` or `notes.md` with wiring and expectations

## Contributing Golden Assets
Golden assets should be:
- deterministic (repeatable output patterns)
- documented (wiring, pins, known limitations)
- verified on a known bench

See also:
- `docs/dut_model.md` for the repo-level DUT architecture model and the distinction between DUT assets, board runtime profiles, and bench/test setup.

## Using `--dut` in CLI
`--dut <id>` resolves DUTs deterministically:
1) `assets_user/duts/<id>/manifest.yaml` (preferred)
2) `assets_golden/duts/<id>/manifest.yaml`

Test/pack selection precedence:
1) explicit `--test` / `--pack`
2) `manifest.default_packs`
3) DUT-local `packs/` or `tests/`
4) error if none

If `configs/boards/<id>.yaml` exists, it is used as the board profile for build/flash defaults.
