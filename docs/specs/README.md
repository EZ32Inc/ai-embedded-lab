# Specs

This directory contains AEL design specs, policies, checkpoints, and draft
records. Many files are versioned or dated design snapshots. Treat them as
current only when they are linked from [../DOCS_INDEX.md](../DOCS_INDEX.md) or
explicitly marked as active.

## Current Reading Order

Start with these public entry points before reading older specs:

- [../README.md](../README.md)
- [../DOCS_INDEX.md](../DOCS_INDEX.md)
- [../architecture_map.md](../architecture_map.md)
- [../ael_cli_reference_v0_1.md](../ael_cli_reference_v0_1.md)
- [../current_validated_capabilities.md](../current_validated_capabilities.md)

## Spec Categories

| Category | Typical files | Status |
|---|---|---|
| Active contracts | `*_contract_*.md`, selected user-project specs | Revalidate against code before citing |
| Policies | `*_policy_*.md`, `*_rules_*.md` | Useful agent/contributor guidance |
| Architecture drafts | `ael_architecture_*`, layer specs | Mixed current/historical |
| Validation schema | result schemas, test schemas, golden-suite specs | Useful for pack and report work |
| Checkpoints and closeouts | `*_checkpoint_*.md`, `*_closeout_*.md` | Historical point-in-time evidence |
| Generated-example planning | `generated_example_*`, `example_*` | Mostly planning history |
| Memos | `Memo:*`, conceptual docs | Historical unless promoted to an active guide |

## Cleanup Rules

- Prefer adding active specs to [../DOCS_INDEX.md](../DOCS_INDEX.md) instead of
  relying on filename discovery.
- Keep dated checkpoint files as history unless they create active confusion.
- Move raw or highly local notes into an archive/raw area after review.
- Replace mixed-language public specs with English versions.
- Do not add new specs with spaces or punctuation-heavy filenames.
