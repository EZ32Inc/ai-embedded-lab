# Documentation Maintenance Policy

Last updated: 2026-06-07

This policy keeps AEL documentation usable for public readers, contributors,
and AI agents.

## Source Of Truth Order

Use this order when docs and implementation disagree:

1. Live CLI output, for example `python3 -m ael --help`
2. Current manifests, packs, target configs, and tests
3. Implementation code
4. Current docs linked from [DOCS_INDEX.md](./DOCS_INDEX.md)
5. Historical reports, archived notes, and dated closeouts

Historical files are evidence. They are not guarantees of current behavior.

## Document Classes

| Class | Location | Rule |
|---|---|---|
| Current entry points | `docs/README.md`, `docs/DOCS_INDEX.md`, core guides | Keep accurate and concise |
| User workflows | `docs/guides/`, selected root docs | Prefer runnable commands and clear prerequisites |
| Board notes | `docs/boards/` | Keep board facts and current validation status separate from dated closeouts |
| Specs | `docs/specs/` | Treat versioned files as point-in-time design records unless explicitly marked current |
| Reports | `docs/reports/` | Preserve validation evidence with dates and pass/fail status |
| Archive | `docs/archive/` | Keep for reference only; do not use as first source |
| Obsolete | `docs/obsolete/` | Remove when it no longer has reference value |
| Non-operational essays | `docs/books/` and concept memos | Do not treat as project instructions |

## Language

Public documentation should be English-first.

- New docs should be written in English.
- Existing Chinese docs should be translated or replaced when they are
  user-facing, contributor-facing, or used as agent guidance.
- Historical Chinese notes may remain temporarily when they are not public
  entry points, but they should be marked or indexed as historical.
- Avoid mixed-language public docs unless the file is explicitly a translation
  pair or migration note.

## File Naming

- Use lowercase snake_case for new docs.
- Include dates in validation reports and closeouts:
  `board_or_area_closeout_YYYY-MM-DD.md`.
- Include a version in stable specs:
  `topic_v0_1.md`.
- Avoid spaces, punctuation, and non-ASCII characters in new filenames.

## Public-Repo Safety

Before committing docs to a public branch, check for:

- private IP addresses and Wi-Fi details
- absolute local paths such as `/home/...` or `/nvme...`
- serial numbers, tokens, keys, certificates, and credentials
- raw terminal logs that include environment-specific data
- unreviewed generated artifacts

Use generic placeholders where the exact value is not essential, for example
`<bench-host-ip>`, `<serial-port>`, or `<repo-root>`.

## Update Checklist

For each documentation cleanup commit:

1. Keep the intent narrow.
2. Update the relevant directory README or index when files move.
3. Run `git diff --check`.
4. Prefer verifying CLI references with `python3 -m ael --help` or the relevant
   subcommand help.
5. Commit immediately after a coherent documentation intent is complete.
