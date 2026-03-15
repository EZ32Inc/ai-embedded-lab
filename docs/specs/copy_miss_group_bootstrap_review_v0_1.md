# AEL Copy-Miss Group Bootstrap — Implementation Review v0.1

Review of `copy_miss_group_bootstrap_feature_v0_1.md` against the current codebase.

---

## A. What in current code already aligns with the feature

### Prefix-to-profile mapping — largely done

`configs/mcu_family_profiles.yaml` already carries the five Tier 1 entries: `stm32`, `rp2` / `rp_`, `esp32` / `esp8266`, `nrf5`. `_infer_family_profile()` loads this file at runtime and does prefix matching. The guard-clean config-file design is exactly right.

### Branch draft creation — done

`_bootstrap_draft_capability()` creates `assets_branch/duts/<slug>_draft/manifest.yaml` and `configs/boards/<slug>_draft.yaml` with `lifecycle_stage: draft`, `draft: true`, and PLACEHOLDER fields. Output structure matches the spec.

### Inventory + lifecycle — done

`inventory.build_inventory()` scans `assets_branch/duts/` and tags entries `source: "branch"`. `_LIFECYCLE_STAGES`, `dut_set_lifecycle_cmd()`, and promote gating are all in place.

### Run-gate for branch capabilities — done

`_project_run_gate_check()` already reads `capability_source: branch` + `capability_ref` from `project.yaml`, checks `lifecycle_stage >= runnable`, and surfaces actionable PLACEHOLDER hints when blocked.

### Scoring for similar golden DUTs — already exists in assets.py

`find_golden_reference()` queries `assets_golden/duts/` and scores by `mcu`, `family`, and `tags` fields. This is exactly what Case B needs. It is not yet wired to the bootstrap path.

### Maturity resolution — separate but related

`_resolve_maturity()` does a family-level partial match (first-7-chars, family prefix strip) to produce `path_maturity: inferred`. This covers Case B detection conceptually, but uses a different code path from `_infer_family_profile()`. These two paths currently diverge.

### Golden DUT inventory — good Group coverage

`assets_golden/duts/` has: `stm32f103`, `stm32f103_gpio`, `stm32f103_uart`, `stm32f401rct6`, `stm32f411ceu6`, `esp32c3_devkit`, `esp32c6_devkit`, `esp32s3_devkit`, `rp2040_pico`, `rp2350_pico2`. Tier 1 Groups (stm32, esp32, rp) all have multiple golden entries available for Case B reference.

---

## B. Biggest gaps between current code and the spec

### Gap 1 — No `group` field in profiles or manifests

`mcu_family_profiles.yaml` has `family` but not `group`. The spec defines Group as a distinct classification unit (stm32 / esp32 / rp / nrf / unknown). Multiple `family` values may belong to one Group (e.g. `rp2040` prefix `rp2` and `rp_` both belong to Group `rp`). Without a `group` field in the profile, Case B reference search has no Group boundary to filter on.

### Gap 2 — Case B is not implemented

`_bootstrap_draft_capability()` does not attempt to find a reference DUT. The spec requires that when a same-Group golden DUT exists, it is used as a structural reference and noted in the draft manifest as `reference_dut`. Currently all bootstraps produce the same PLACEHOLDER skeleton regardless of Group coverage.

### Gap 3 — `_resolve_maturity()` and `_infer_family_profile()` diverge

`_resolve_maturity()` drives the `is_unknown` / `is_inferred` branching in `_project_create_shell()`. `_infer_family_profile()` drives the bootstrap profile selection. They use different matching logic (first-7-chars heuristic vs prefix table). When `_resolve_maturity()` returns `inferred`, the bootstrap doesn't run at all — yet Case B says that "same Group has similar known support" is exactly when bootstrap *with* a reference should run. This logic split is the main structural gap.

### Gap 4 — Profiles lack `group`, `first_test_archetype`, `verification_style`

The spec defines these as Group profile fields. Currently `mcu_family_profiles.yaml` has only `prefix`, `family`, `build_type`, `flash_method`, `instrument_hint`. Adding `group`, `first_test_archetype`, and optionally `verification_style` is a small config-only change.

### Gap 5 — Draft manifest missing `group` and `reference_dut` fields

Bootstrapped manifests currently have: `id`, `mcu`, `family`, `build_type`, `flash_method`, `lifecycle_stage`, `verified`, `capability_notes`, `board_config`. Spec requires `group` and (for Case B) `reference_dut`. Two new optional manifest fields.

### Gap 6 — `is_inferred` branch does not trigger bootstrap

When `_resolve_maturity()` returns `path_maturity: inferred`, `_project_create_shell()` sets `status: exploratory` and asks clarification questions, but does not bootstrap. Under the new spec, `inferred` is effectively Case B: same Group, similar but not exact. Bootstrap should run here, not stop at clarification.

---

## C. Recommended minimal implementation direction

The implementation has five tightly scoped changes. All are additive — no existing behavior needs to be removed.

### Step 1 — Add `group` field to `mcu_family_profiles.yaml`

Add `group: "stm32"` / `"esp32"` / `"rp"` / `"nrf"` to each entry. This is a pure config change. `_infer_family_profile()` reads and returns it with no code change beyond adding `"group"` to the returned dict. The unknown fallback returns `group: "unknown"`.

```yaml
# example
- prefix: "stm32"
  group: "stm32"
  family: "stm32"
  build_type: "arm_debug"
  flash_method: "gdb_swd"
  instrument_hint: "esp32jtag or st-link (SWD)"
  first_test_archetype: "gpio_signature"
```

### Step 2 — Add `_find_group_reference(group, mcu_name)` function

A small function wrapping `assets.find_golden_reference()` with a Group filter:

```python
def _find_group_reference(group: str, mcu_name: str) -> dict | None:
    # Filter golden DUTs to those whose manifest.family starts with the Group
    # Use existing find_golden_reference() scoring but pre-filter by group
```

This reuses the existing scoring mechanism. No new scoring logic needed.

### Step 3 — Update `_bootstrap_draft_capability()` to accept optional `reference_dut`

Add an optional `reference_dut: dict | None` parameter. When provided:
- Write `reference_dut: <dut_id>` to the manifest
- Copy `build_type` and `flash_method` from reference manifest (already done via Group profile)
- Optionally seed `observe_map` pattern from reference if structure matches

When not provided, behavior is unchanged.

### Step 4 — Wire Case B into `_project_create_shell()`

When `is_inferred` (not just `is_unknown`): also run bootstrap, call `_find_group_reference()`, pass result to `_bootstrap_draft_capability()`.

Specifically:
- `is_inferred` → Case B bootstrap with `reference_dut` set
- `is_unknown` → Case C or D bootstrap (existing behavior, now adds `group` field)

This removes the current "ask clarifications and stop" behavior for `inferred` and replaces it with "bootstrap with reference + show clarifications".

### Step 5 — Write `group` field into manifest during bootstrap

One-line addition to the manifest dict in `_bootstrap_draft_capability()`:
```python
"group": profile.get("group", "unknown"),
```

---

## D. Recommended first-pass Groups and Cases

### Tier 1 Groups (implement fully)

- **stm32** — 5 golden DUTs available, Case B reference lookup will find good matches
- **esp32** — 3 golden DUTs available (c3, c6, s3), diverse enough for family-level reference
- **rp** — 2 golden DUTs (pico, pico2), sufficient for Case B

Tier 1 Groups should have `first_test_archetype: "gpio_signature"` in their profiles, matching what all three families already use in golden.

### Tier 2 Group (lighter treatment)

- **nrf** — no golden DUTs yet, so Case B will fall through to Case C. Profile fields work, but reference lookup returns nothing. This is fine — Case C is the correct behavior. No special handling needed.

### Cases to implement in first pass

**Case A** — already works (exact golden match → copy-first). No change needed.

**Case B** — implement in Step 2–4 above. Testable with `stm32f412` (matches stm32f411ceu6 as reference), `esp32h2` (matches esp32c6 as reference), `rp2350` variant (matches rp2040_pico or rp2350_pico2).

**Case C** — already works functionally (is_unknown path today). Upgrade: add `group` to manifest, add `group_note` when group is identified. Minimal delta.

**Case D** — already works (unknown fallback). Upgrade: add `group_note: "MCU group not recognized"` to manifest. One line.

### Cases to defer

Case B reference scoring refinement (beyond simple family-prefix match) — defer. The existing `find_golden_reference()` scoring is sufficient for Tier 1 validation.

---

## E. What should explicitly wait until later

| Item | Reason |
|---|---|
| `first_test_archetype` driving automated test plan generation | Requires test plan scaffolding logic not yet designed |
| `verification_style` field influencing bootstrap output | No consuming code path yet |
| Case B `observe_map` seeding from reference board config | Fragile without MCU-pin compatibility check; PLACEHOLDER is safer |
| Sub-family taxonomy within stm32 (F4 vs H7 vs L4) | Not needed until Tier 1 is validated |
| nrf golden DUT creation | Separate onboarding task; Group bootstrap still works without it (Case C) |
| Advanced Case B scoring (tags, clock_hz, pin count) | Simple family-prefix match is sufficient for first pass |
| `group_note` in board config (currently only in manifest) | Low value; manifest note is sufficient |
| Any change to `_resolve_maturity()` beyond the is_inferred→bootstrap wiring | It works; don't touch it more than needed |

---

## F. Do now / do later / not yet

### Do now (first-pass implementation)

1. Add `group` + `first_test_archetype` to `mcu_family_profiles.yaml` (config-only, no code)
2. Add `_find_group_reference(group, mcu_name)` — ~15 lines, wraps existing scoring
3. Extend `_bootstrap_draft_capability()` to accept + write `reference_dut` — minimal addition
4. Wire `is_inferred` branch in `_project_create_shell()` to run Case B bootstrap — replaces the "ask clarifications and stop" with "bootstrap with reference + show clarifications"
5. Add `group` field to bootstrapped manifests — one line

### Do later (after first-pass is validated)

- Add test cases for all four Cases (A/B/C/D), one per Tier 1 Group
- Enrich Group profiles with `verification_style` once a consuming path exists
- Consider nrf golden DUT creation to make Case B testable for that Group
- Sub-family scoring refinement once Case B is exercised in practice

### Not yet

- Automated test plan generation from `first_test_archetype`
- Board config completion beyond PLACEHOLDER
- Multi-chip / multi-board bootstrap
- Deep per-vendor taxonomy
- Any change to lifecycle, inventory, or promote paths — they are already complete

---

## Commentary on Tier priority

**stm32 / esp32 / rp as Tier 1** is correct. These three Groups have golden entries available, so Case B reference lookup will actually find something useful. The bootstrap output will be meaningfully populated — not just a blank skeleton. This makes the feature demonstrably better than the current behavior for these Groups.

**nrf as Tier 2** is correct. The Group profile works, the bootstrap runs, but there is no golden reference yet. Case C output is the right result. No special treatment needed — just ensure `group: nrf` appears in the manifest so the developer knows which Group was identified.

**unknown fallback** must remain. Any MCU not matching a prefix should still produce a usable scaffold. The `group_note` addition is the only improvement needed here.

The feature is ready to implement in one focused session. Total estimated code delta: ~60 lines across two functions + one config file update. No existing behavior is broken; all changes are additive.

---

*Review version: v0.1 — implementation-aware, bounded scope.*
