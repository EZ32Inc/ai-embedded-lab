# Codebase Size Report

Prepared: 2026-03-18

## Scope

This report summarizes the current size and rough complexity of the AEL repository.

The raw repo total is misleading because bundled third-party code dominates the line count. The more useful view is:

- full repo
- repo excluding `third_party/`
- practical first-party AEL footprint

## Headline Numbers

### Full repo

- files: `22,529`
- lines: `21,749,644`

### Excluding `third_party/`

- files: `1,534`
- lines: `329,943`

### Excluding `third_party/` and bundled STLink upstream/install trees

- files: `1,326`
- lines: `299,740`

### Practical AEL footprint

Directories counted:

- `ael`
- `tests`
- `tools`
- `configs`
- `packs`
- `projects`
- `docs`
- `firmware`
- `assets_golden`

Totals:

- files: `1,285`
- lines: `295,107`

## Main Areas By Size

| Area | Files | Lines |
|---|---:|---:|
| `firmware` | 417 | 149,676 |
| `assets_golden` | 184 | 57,557 |
| `docs` | 327 | 47,091 |
| `ael` | 79 | 20,948 |
| `tests` | 164 | 12,306 |
| `tools` | 40 | 4,713 |
| `configs` | 52 | 2,269 |
| `projects` | 9 | 392 |
| `packs` | 13 | 155 |

## Code Shape By File Type

Selected authored areas:

| Pattern | Files | Lines |
|---|---:|---:|
| `ael/*.py` | 78 | 20,846 |
| `tests/*.py` | 49 | 7,286 |
| `tools/*.py` | 29 | 3,873 |
| `firmware/*.c` | 102 | 14,706 |
| `firmware/*.h` | 17 | 52,098 |
| `firmware/Makefile` | 61 | 2,309 |
| `configs/*.yaml` | 40 | 1,821 |
| `docs/*.md` | 315 | 44,069 |

## Largest Core Python Modules

| File | Lines |
|---|---:|
| `ael/__main__.py` | 3,585 |
| `ael/pipeline.py` | 2,092 |
| `ael/adapter_registry.py` | 1,184 |
| `ael/default_verification.py` | 851 |
| `ael/inventory.py` | 729 |
| `ael/instruments/usb_uart_bridge_daemon.py` | 718 |
| `ael/connection_model.py` | 668 |
| `ael/strategy_resolver.py` | 601 |
| `ael/stage_explain.py` | 506 |
| `ael/instrument_view.py` | 496 |

## Classification

### Size

This is:

- not a small project
- medium-sized in first-party core code
- medium-to-large as a repository

### Complexity

This is a high-complexity project relative to its line count.

Reasons:

- it spans Python orchestration, firmware targets, bench/instrument control, validation, inventory, and docs/spec layers
- a large amount of behavior is config-driven rather than concentrated in code
- the system touches real hardware, so operational complexity is much higher than a typical CLI app
- a few large central modules carry a lot of coordination responsibility

## What This Means

The main challenge is not raw code volume. The main challenge is keeping these layers aligned:

- runtime behavior
- test expectations
- board/instrument configs
- inventory and status surfaces
- docs and milestone claims

For project management, this means:

- changes need stronger source-of-truth discipline
- large central files should be reduced over time
- canonical test entrypoints should be explicit
- default verification and repo status should stay trustworthy

## Recommended Focus

Highest-value maintenance work:

1. Reduce source-of-truth drift between docs, status, configs, and tests.
2. Split oversized central modules such as `ael/__main__.py` and `ael/pipeline.py`.
3. Define one supported Python test entrypoint and scope test discovery cleanly.
4. Keep default verification green and accurate before expanding board coverage.

