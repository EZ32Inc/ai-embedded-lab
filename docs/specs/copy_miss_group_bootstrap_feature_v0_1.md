# AEL Copy-Miss Group Bootstrap Feature v0.1

## 1. Purpose

### Why copy-miss should not remain a dead end

When a user requests a board or MCU that has no existing mature capability in `assets_golden/`, AEL currently bootstraps a minimal draft using ad hoc per-MCU prefix matching. This works for simple cases but has no structure: the bootstrap rules are not grouped, not testable by category, and not extensible without modifying core logic.

A copy-miss should produce a consistent, structured starting point — not a one-off artifact whose quality depends on which prefix happened to match.

### Why bootstrap should be grouped rather than per-board ad hoc

Different MCU families share toolchain assumptions, debug/flash styles, and typical test archetypes. An STM32 and an nRF52 both use SWD and GDB-based flashing; an ESP32 uses esptool over UART. A Group captures these shared assumptions as a reusable bootstrap profile.

Per-board ad hoc logic cannot be tested systematically, cannot be enriched incrementally, and produces inconsistent output across families. Group-based rules can be tested one Group at a time and improved without touching unrelated Groups.

### Why this feature is useful even when many boards are already supported

Most MCU variants that appear in real use are not already in `assets_golden/`. New silicon, new board variants, customer-specific MCUs — all trigger copy-miss. The Group bootstrap provides a predictable on-ramp rather than a blank slate, regardless of how many golden entries already exist.

### Why this feature is testable and bounded

Each Group is a discrete unit with defined bootstrap behavior. A test suite can cover one mature-hit case, one same-group bootstrap case, one generic-group bootstrap case, and one unknown fallback case. The feature is complete when all four cases produce correct output. No deep taxonomy or automated inference is required to validate it.

---

## 2. Core Feature Definition

**Copy-first still applies.** The user-facing principle is unchanged: if a mature capability exists in `assets_golden/`, it is reused directly. Group bootstrap runs only when reuse fails.

**Feature trigger:** copy-miss — no mature capability in `assets_golden/` matches the requested MCU/board closely enough to reuse.

**Feature action:** identify the MCU Group, apply the Group's bootstrap profile, create a branch draft capability in `assets_branch/duts/`.

**Feature output:** a branch draft capability at `lifecycle_stage: draft`. The draft then follows the existing capability lifecycle (`draft → runnable → validated → merge_candidate → merged_to_main`).

**Main capability is not affected.** Bootstrap never writes to `assets_golden/`. The output is always a branch artifact.

**Project linkage is automatic.** The creating project's `project.yaml` is updated with `capability_source: branch` and `capability_ref: <dut_id>`.

---

## 3. Group Model

Group is the primary classification unit for bootstrap behavior. A Group represents a vendor/family cluster that shares toolchain, debug/flash, and test archetype assumptions.

### Initial Groups

| Group id | MCU name prefixes | Notes |
|---|---|---|
| `stm32` | `stm32*` | STMicroelectronics Cortex-M family |
| `esp32` | `esp32*`, `esp8266*` | Espressif SoC family |
| `rp` | `rp2*`, `rp_*` | Raspberry Pi RP-series |
| `nrf` | `nrf5*`, `nrf9*` | Nordic Semiconductor |
| `unknown` | (no prefix match) | Fallback for unrecognized MCUs |

Group identification is based on MCU name prefix matching (case-insensitive). The Group list is defined in `configs/mcu_family_profiles.yaml` and is the authoritative source. Adding a new Group does not require code changes — only a new entry in the config file.

---

## 4. Group Behavior Model

Each Group carries a bootstrap profile. The profile defines the default assumptions used when creating the branch draft capability. These are starting-point assumptions, not verified facts — the developer must review and fill placeholders before the capability is runnable.

### Profile fields per Group

| Field | Meaning |
|---|---|
| `build_type` | Build toolchain type (e.g. `arm_debug`, `idf`, `pico`) |
| `flash_method` | Default flash/load mechanism (e.g. `gdb_swd`, `idf_esptool`) |
| `instrument_hint` | Likely debug/flash instrument for human guidance |
| `first_test_archetype` | Typical first test type for this Group (e.g. `gpio_signature`, `uart_banner`) |
| `placeholder_fields` | List of fields in board config that require manual fill-in |
| `verification_style` | How verification is typically done (e.g. `oscilloscope_capture`, `uart_read`) |

### Group profiles (initial values)

**stm32**
- build_type: `arm_debug`
- flash_method: `gdb_swd`
- instrument_hint: SWD adapter (ST-Link, ESP32JTAG, J-Link)
- first_test_archetype: `gpio_signature`
- placeholder_fields: `clock_hz`, `instrument_instance`, `bench_connections`, `safe_pins`, `observe_map`
- verification_style: `oscilloscope_capture`

**esp32**
- build_type: `idf`
- flash_method: `idf_esptool`
- instrument_hint: USB/UART or ESP-PROG
- first_test_archetype: `gpio_signature`
- placeholder_fields: `instrument_instance`, `bench_connections`, `observe_map`
- verification_style: `oscilloscope_capture`

**rp**
- build_type: `pico`
- flash_method: `gdb_swd`
- instrument_hint: picoprobe or SWD adapter
- first_test_archetype: `gpio_signature`
- placeholder_fields: `instrument_instance`, `bench_connections`, `observe_map`, `safe_pins`
- verification_style: `oscilloscope_capture`

**nrf**
- build_type: `arm_debug`
- flash_method: `gdb_swd`
- instrument_hint: J-Link or SWD adapter
- first_test_archetype: `gpio_signature`
- placeholder_fields: `clock_hz`, `instrument_instance`, `bench_connections`, `safe_pins`, `observe_map`
- verification_style: `oscilloscope_capture`

**unknown**
- build_type: `PLACEHOLDER_build_type`
- flash_method: `PLACEHOLDER_flash_method`
- instrument_hint: unknown — specify debug/flash instrument
- first_test_archetype: `PLACEHOLDER_test_archetype`
- placeholder_fields: all fields
- verification_style: `PLACEHOLDER_verification_style`

---

## 5. Reuse / Similarity / Fallback Cases

There are four distinct cases the feature must handle. These determine how the bootstrap profile is applied and what reference (if any) is used to populate the draft.

### Case A — Mature known support exists

**Condition:** an entry in `assets_golden/duts/` matches the requested MCU/board closely enough for direct reuse.

**Action:** copy-first applies. No bootstrap runs. The project links to the golden capability directly (`capability_source: main`).

**Output:** existing golden capability, `capability_ref` points to the golden DUT id.

---

### Case B — Same Group has similar known support, but not exact target

**Condition:** no exact golden match, but the MCU belongs to a Group that has at least one mature golden entry for a related MCU/board.

**Action:** Group bootstrap runs. The most similar golden DUT within the Group is identified and used as a structural reference (field values, observe_map style, bench_connections pattern). The reference is noted in the draft manifest as `reference_dut`. PLACEHOLDER fields that cannot be inferred from the reference are still marked as PLACEHOLDER.

**Output:** branch draft capability with partial field population from the reference DUT. `lifecycle_stage: draft`. Project gets `capability_source: branch`.

**Example:** user requests `stm32f412`, golden has `stm32f411ceu6`. Bootstrap uses `stm32f411ceu6` as reference; copies clock_hz and observe_map pattern; marks instrument_instance and bench_connections as PLACEHOLDER (may differ for the specific board).

---

### Case C — Group identified, but no similar known support exists

**Condition:** MCU belongs to a recognized Group, but the Group has no mature golden entries to use as reference.

**Action:** Group bootstrap runs using only the Group's default profile. All board-specific fields are PLACEHOLDER. The Group provides build_type, flash_method, and instrument_hint.

**Output:** branch draft capability fully from Group profile defaults. All board-specific fields are PLACEHOLDER. `lifecycle_stage: draft`.

**Example:** user requests `nrf52840`, Group is `nrf`, no golden nrf entries exist. Bootstrap creates the draft with `arm_debug` / `gdb_swd` profile and all PLACEHOLDER board fields.

---

### Case D — Group cannot be identified

**Condition:** MCU name prefix matches no known Group.

**Action:** `unknown` Group bootstrap runs. All profile fields are PLACEHOLDER. The draft is created as a pure scaffold with no assumptions.

**Output:** branch draft capability with all fields PLACEHOLDER. `lifecycle_stage: draft`. A note is added to the manifest: `group_note: "MCU group not recognized — all profile fields require manual fill-in"`.

---

## 6. Bootstrap Output Expectations

A successful bootstrap produces the following minimal set of artifacts:

**Branch DUT manifest** (`assets_branch/duts/<slug>_draft/manifest.yaml`)
- `id`: `<mcu_slug>_draft`
- `mcu`: original MCU name as provided
- `group`: Group id used
- `family`: Group family value
- `build_type`: from Group profile (or PLACEHOLDER)
- `flash_method`: from Group profile (or PLACEHOLDER)
- `lifecycle_stage`: `draft`
- `verified`: `{status: false, note: "draft — not yet verified"}`
- `reference_dut`: id of reference golden DUT if Case B applies, else absent
- `capability_notes`: human-readable summary of bootstrap origin and what needs filling
- `board_config`: path to the generated board config file

**Board config skeleton** (`configs/boards/<slug>_draft.yaml`)
- `board.draft: true` — prevents inventory from treating this as a production config
- `board.name`: PLACEHOLDER with MCU name embedded
- `board.target`: MCU slug
- `board.build.type`: from Group profile
- `board.flash`: PLACEHOLDER fields where not inferable from reference
- `board.observe_map`: PLACEHOLDER or copied from reference DUT if Case B
- `board.bench_connections`: PLACEHOLDER
- `board.instrument_instance`: PLACEHOLDER with instrument_hint as comment

**Project linkage** (in `project.yaml`)
- `capability_source: "branch"`
- `capability_ref: "<slug>_draft"`
- `cross_domain_links`: entry with `type: branch_capability_ref`

**Human-readable next actions** (printed at creation time and in README.md)
- List of PLACEHOLDER fields that require manual fill-in
- Suggested next commands (`ael dut set-lifecycle`, `ael dut promote`)
- Reference DUT name if Case B applies

---

## 7. Initial Scope

### This version should NOT attempt

- Fully resolving all MCU variants within a Group automatically
- Completing board config without PLACEHOLDER fields
- Replacing developer review of generated artifacts
- Automatically selecting the best test archetype beyond the Group default
- Handling multi-chip boards, custom PCBs, or complex instrument setups
- Inferring clock speed, pin assignments, or observe_map from MCU name alone
- Any large refactor of the existing bootstrap code path

### This version SHOULD achieve

- A consistent bootstrap output for all four cases (A/B/C/D)
- Every case testable independently
- Group rules fully defined in `configs/mcu_family_profiles.yaml` (no Group logic in core code)
- Case B reference DUT selection using a simple scoring heuristic (MCU family match score)
- Clear PLACEHOLDER markers wherever the developer must act
- Output that can be used as-is at `lifecycle_stage: draft` and advanced manually

### What "good enough" looks like

A developer receives a bootstrap output, opens the board config, sees clearly labeled PLACEHOLDER fields, fills them in, runs `ael dut set-lifecycle --id <id> --stage runnable`, and can proceed to run. No fields are silently wrong — either they are correct from the Group profile, or they are explicitly marked PLACEHOLDER.

---

## 8. Testing / Validation Concept

The feature is validated by four test cases, one per case type.

**Test 1 — Case A (mature hit):** request an MCU already in `assets_golden/` (e.g. `stm32f411ceu6`). Verify: no bootstrap runs, project links to golden capability, `capability_source: main`.

**Test 2 — Case B (same-group reference):** request an MCU whose Group has a golden entry but the exact MCU is not in golden (e.g. `stm32f412`). Verify: bootstrap runs, `reference_dut` is set in manifest, at least one field is populated from the reference (e.g. `build_type`), board config contains PLACEHOLDER for board-specific fields.

**Test 3 — Case C (group, no reference):** request an MCU whose Group has no golden entries (e.g. an nRF MCU when no nRF golden DUTs exist). Verify: bootstrap runs, Group profile fields are applied (build_type, flash_method), all board-specific fields are PLACEHOLDER, manifest has no `reference_dut`.

**Test 4 — Case D (unknown group):** request an MCU with an unrecognized prefix (e.g. `ch32v003`). Verify: `unknown` Group is used, all fields are PLACEHOLDER, `group_note` is present in manifest.

For all cases B/C/D: verify `lifecycle_stage: draft`, `capability_source: branch` in project.yaml, and that `ael project run-gate` blocks with an actionable message about filling PLACEHOLDERs.

---

## 9. Deferred Complexity

The following are explicitly out of scope for this version:

| Item | Reason deferred |
|---|---|
| Deep per-vendor sub-family taxonomy (e.g. STM32F4 vs STM32H7 vs STM32L4) | Not needed until Group-level bootstrap is validated |
| Automatic clock_hz inference from MCU part number | Requires MCU database; too broad for this feature |
| Automatic pin assignment or LED pin inference | Not solvable without board-level data |
| Advanced Case B reference scoring beyond MCU family match | Simple heuristic is sufficient for v0.1 |
| Branch governance for Group-generated capabilities | Existing lifecycle model is sufficient |
| Full automation of board config completion | PLACEHOLDER + manual review is the v0.1 contract |
| Multi-chip or multi-board project bootstrap | Single DUT bootstrap only |
| Group-specific test plan generation | Group provides archetype hint only; test plan is manual |
| Any large refactor of inventory, pipeline, or run paths | Feature is additive to existing paths |

---

*Feature version: v0.1 — group-based copy-miss bootstrap, bounded scope.*
