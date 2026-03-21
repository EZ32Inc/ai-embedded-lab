# DUT Standardization Implementation / Migration Plan v0.1

**Status:** Draft
**Date:** 2026-03-21
**Companion spec:** `docs/dut_standardization_spec_v0_1.md`

---

## 1. Goal

Migrate the AEL platform from its current two-file, MCU-centric DUT representation to a board-first, capability-declared, interface-backed DUT model — without breaking any currently verified boards or active execution paths.

The migration is complete when:

- Every verified DUT board has a `processors[]` list, declared `capabilities`, and at least one `verification_profiles` entry.
- `ael/dut/interfaces/` provides a stable `DUTProvider` interface used by at least one active execution path.
- `assets.py` no longer requires the flat `mcu` field.
- `find_golden_reference()` queries against `processors[]` fields, not flat `mcu`/`family` strings.
- At least one `default_verification` worker path goes through the DUT registry rather than direct dict access.

---

## 2. Migration Strategy

**Progressive, adapter-first. Not a big-bang rewrite.**

The instrument interface migration (`ael/instruments/interfaces/`) is the proven pattern to follow. That migration introduced a thin `InstrumentProvider` interface wrapping existing behavior, then gradually moved logic behind it. At no point did it require rewriting all callers simultaneously.

The DUT migration follows the same principle:

1. Create the interface layer first.
2. Create an adapter that wraps the existing two-file model.
3. Route one execution path through the new interface.
4. Migrate board definitions one at a time.
5. Delete the old paths only when all paths go through the new interface.

**Never break verified boards.** `rp2040_pico` (verified), `stm32f103` (verified), and `stm32g431cbu6` (verified) are the regression anchors. Any phase that breaks a passing run on one of these boards is a rollback.

---

## 3. Current-State Assessment

### 3.1 Two-File Problem

Each DUT requires two separate files maintained in sync:

| File | Location | Contains |
|---|---|---|
| DUT manifest | `assets_golden/duts/<id>/manifest.yaml` | id, mcu (single string), family, build, flash, tags, verified |
| Board config | `configs/boards/<id>.yaml` | name, target, instrument_instance, observe_map, verification_views, bench_connections, wiring, power/boot |

There is no formal link between these two files. A board config references no manifest; a manifest references no board config. They share only the convention that their filenames use the same `<id>` string.

**Currently confirmed boards with both files:**

| DUT ID | manifest.yaml | board config |
|---|---|---|
| `rp2040_pico` | Yes | `configs/boards/rp2040_pico.yaml` |
| `rp2350_pico2` | Yes | `configs/boards/rp2350_pico2.yaml` |
| `stm32g431cbu6` | Yes | `configs/boards/stm32g431cbu6.yaml` |
| `stm32h750vbt6` | Yes | `configs/boards/stm32h750vbt6.yaml` |
| `stm32f411ceu6` | Yes | `configs/boards/stm32f411ceu6.yaml` |
| `esp32c6_devkit` | Yes | `configs/boards/esp32c6_devkit.yaml` |
| `esp32c3_devkit` | Yes | `configs/boards/esp32c3_devkit.yaml` |
| `esp32s3_devkit` | Yes | `configs/boards/esp32s3_devkit.yaml` |

Some board configs have no corresponding manifest (e.g., `configs/boards/stm32f030c8t6.yaml`, `stm32f407_discovery.yaml`). These boards are not yet registered as DUT assets.

### 3.2 `mcu` Single-Field Problem

`ael/assets.py` `_REQUIRED_FIELDS` list (confirmed in source):

```python
_REQUIRED_FIELDS = [
    "id",
    "mcu",       # <-- single string, not processors[]
    "family",
    "description",
    ("build", "type"),
    ("build", "project_dir"),
    ("flash", "method"),
    ("verified", "status"),
]
```

`find_golden_reference()` in `ael/assets.py` scores candidates against `manifest.get("mcu")` and `manifest.get("family")`. This is MCU-centric: it assumes one MCU per DUT and treats `mcu` as the primary identity signal.

### 3.3 No `ael/dut/` Interface Layer

`ael/dut/` does not exist. There is no:
- `DUTProvider` interface class
- DUT registry
- DUT loader that merges manifest + board config
- `DUTInstance` runtime class

Code that needs board information reads raw dicts directly. Examples:
- `pipeline.py` reads board config via `_simple_yaml_load()` and passes the raw dict to adapters.
- `default_verification.py` reads probe config and board config as separate dicts and merges them inline.
- `assets.py` `load_dut()` returns a raw dict with a `manifest` key; callers access `entry["manifest"].get("mcu")` directly.

### 3.4 No Runtime DUT Instance Class

Runtime execution does not construct a DUT object. Instead, a run is built around:
- A raw board config dict (loaded from `configs/boards/<id>.yaml`)
- A probe config dict (loaded from instrument instance config)
- A test plan dict (loaded from pack file)

DUT identity appears in run outputs as `dut_id` string fields, but there is no Python object representing the current DUT in a run.

### 3.5 Verification Logic Scattered

Verification behavior is spread across:

| File | Role |
|---|---|
| `ael/default_verification.py` | Orchestrates verification runs: worker setup, scheduling, result collection |
| `ael/pipeline.py` | Runs individual pipeline steps including verify substages |
| `configs/boards/<id>.yaml` → `verification_views` | Per-board named scenarios with pin mappings |
| `ael/verification_model.py` | `VerificationSuite`, `VerificationTask`, `VerificationWorker` dataclasses |
| `ael/verify_default_snapshot.py` | Snapshot-based verification comparison |

`verification_views` in board configs is the closest existing analog to `verification_profiles` as defined in the spec. However, it is not formally validated, not capability-linked, and not surfaced through any interface — it is read as a plain dict key.

### 3.6 `find_golden_reference()` is MCU-Centric

`find_golden_reference()` scores candidate DUTs by matching `mcu` (100 pts), `family` (50 pts), and tag intersection (5 pts/tag). This works for single-MCU boards but fails for:
- Boards where multiple variants share the same MCU string.
- Future composite boards with more than one entry in `processors[]`.
- Cases where the board ID is the better anchor than the MCU string.

---

## 4. Target Architecture

After migration, the DUT layer will look like this:

```
[Static Assets]
  assets_golden/duts/<id>/manifest.yaml   (board definition — unified schema)
  configs/processors/<mcu>.yaml           (processor profiles — shared)

[Interface Layer]
  ael/dut/interfaces/base.py              (DUTProvider dataclass)
  ael/dut/interfaces/registry.py          (resolve_dut_provider, load_board_definition)
  ael/dut/backends/manifest_adapter.py    (wraps manifest + board config dicts)

[Runtime Layer]
  ael/dut/runtime/dut_instance.py         (DUTInstance: bound instrument, session, status)

[Callers updated]
  ael/assets.py                           (_REQUIRED_FIELDS uses processors[0].id)
  ael/pipeline.py                         (loads DUT via registry, not raw dict)
  ael/default_verification.py             (worker setup uses DUTInstance)
```

---

## 5. Phased Implementation Plan

### Phase 0: Inventory and Assessment (No code changes)

**Goal:** Confirm current state before writing anything.

Tasks:
- List all DUT IDs in `assets_golden/duts/` and confirm which have matching `configs/boards/<id>.yaml`.
- List all board configs that have no DUT manifest.
- Document which boards have `verified.status: true`.
- Identify any callers that read `manifest.get("mcu")` directly.

**Exit gate:** A confirmed list of all boards, their file pairs, and their verified status. No regressions possible.

---

### Phase 1: Create the Interface Skeleton

**Goal:** `ael/dut/` directory exists with stub files. No callers changed.

Tasks:
- Create `ael/dut/__init__.py`
- Create `ael/dut/interfaces/__init__.py`
- Create `ael/dut/interfaces/base.py` with `DUTProvider` dataclass (stub callables returning `{}`)
- Create `ael/dut/interfaces/registry.py` with `resolve_dut_provider()` returning `None` for all inputs
- Create `ael/dut/runtime/__init__.py`
- Create `ael/dut/runtime/dut_instance.py` with a minimal `DUTInstance` dataclass

**Exit gate:** `ael/dut/` imports without error. No test regressions.

---

### Phase 2: Create the Manifest Adapter Backend

**Goal:** A `DUTProvider` implementation that wraps the existing two-file model.

Tasks:
- Create `ael/dut/backends/__init__.py`
- Create `ael/dut/backends/manifest_adapter.py`
  - `identify()`: returns `id`, `mcu` (from manifest), `family`, `board_class: "standard"` (default)
  - `get_capabilities()`: returns empty list (not yet declared in manifests)
  - `get_verification_profiles()`: reads `verification_views` from board config if available
  - `list_processors()`: returns `[{"id": manifest["mcu"], "family": manifest["family"], "role": "primary"}]` — wraps the single `mcu` field as a one-element processors list for compatibility
- Register the adapter in `ael/dut/interfaces/registry.py`

**Exit gate:** `load_board_definition("rp2040_pico")` returns a `DUTProvider` that satisfies all interface methods without loading anything new.

---

### Phase 3: Migrate `assets.py` Schema to `processors[]`

**Goal:** `_REQUIRED_FIELDS` accepts `processors[0].id` in addition to `mcu`. Both are accepted during transition.

Tasks:
- Add `processors` to `_REQUIRED_FIELDS` as an optional-then-required field with a deprecation warning path.
- Update `_validate_manifest()` to accept either `mcu` (legacy) or `processors[0].id` (new).
- Update `find_golden_reference()` to score against both `manifest.get("mcu")` and `processors[0].id` for compatibility.
- Add a warning log when `mcu` is present and `processors` is absent, so old manifests are visible.

**Exit gate:** All existing manifests still pass `_validate_manifest()`. New manifests with `processors[]` and no `mcu` also pass.

---

### Phase 4: Add `board_class` and `capabilities` to Two Boards

**Goal:** Two boards are migrated to the new unified schema as a pilot.

Recommended pilot boards (start with verified boards to catch regressions immediately):
1. `rp2040_pico` — `verified.status: true`, simplest single-processor board
2. `stm32g431cbu6` — `verified.status: true` (assumed), has the most complete `verification_views`

Tasks for each board:
- Add `board_class: standard`
- Add `processors:` list replacing or supplementing `mcu: <string>`
- Add `capabilities:` list (derive from existing `build.type` and `flash.method`)
- Add `verification_profiles:` block (derived from existing `verification_views`)
- Do not yet remove `mcu` — keep it as a deprecated alias
- Run verification against both boards to confirm no regression

**Exit gate:** Both pilot boards pass their existing verification runs. `list_duts()` still returns them as valid.

---

### Phase 5: Create `configs/processors/` Processor Profiles

**Goal:** Shared processor profiles exist for the MCUs in the pilot boards.

Tasks:
- Create `configs/processors/rp2040.yaml`
- Create `configs/processors/stm32g431cbu6.yaml`
- Update pilot board manifests to reference processor profiles by ID

**Exit gate:** Processor profiles parse correctly. DUT adapter can resolve processor info from profiles.

---

### Phase 6: Route One Execution Path Through DUT Registry

**Goal:** At least one live execution path reads board info via `ael/dut/interfaces/registry.py` instead of raw dict access.

Recommended path: `default_verification.py` worker setup for `rp2040_pico`.

Tasks:
- In `default_verification.py`, add a call to `resolve_dut_provider(board_id)` before building the worker.
- Use `provider.get_verification_profiles(board_def)` to fetch the verification scenario.
- Fall back to old `verification_views` dict access if no provider is found (backwards compatibility).

**Exit gate:** `rp2040_pico` default verification run succeeds via the new path. All other boards continue using the old path.

---

### Phase 7: Migrate Remaining Verified Boards

**Goal:** All boards with `verified.status: true` have `board_class`, `processors[]`, `capabilities`, and `verification_profiles`.

Boards in scope (confirmed verified or likely verified based on codebase):
- `rp2040_pico` (done in Phase 4)
- `stm32g431cbu6` (done in Phase 4)
- `stm32f103` family variants
- `stm32f411ceu6`
- `stm32h750vbt6`

**Exit gate:** All verified boards pass schema validation and their existing verification runs.

---

### Phase 8: Migrate Unverified Boards

**Goal:** All boards in `assets_golden/duts/` have the new schema fields, even if `verified.status` is false.

Boards in scope: `esp32c6_devkit`, `esp32c3_devkit`, `esp32s3_devkit`, `rp2350_pico2`.

**Exit gate:** `list_duts()` returns all boards as valid under the new schema. No `_validate_manifest()` warnings.

---

### Phase 9: Add Board Definitions for Orphaned Board Configs

**Goal:** Every `configs/boards/<id>.yaml` has a corresponding DUT manifest.

Boards to add manifests for (confirmed to have board configs but no manifest today):
- `stm32f030c8t6`
- `stm32f407_discovery`
- `stm32f407vg` (draft)
- `stm32f401ce` (draft)
- `stm32f756bgt6`
- Various `_stlink` variant configs

**Exit gate:** `list_duts()` count matches the number of board configs.

---

### Phase 10: Create `DUTInstance` Runtime Class and Bind It

**Goal:** The `DUTInstance` class is used in at least one active run as the carrier for bound instrument and session state.

Tasks:
- Implement `ael/dut/runtime/dut_instance.py` with fields: `board_id`, `board_def`, `provider`, `instrument_instance`, `session_id`, `status`.
- In `pipeline.py`, construct a `DUTInstance` at run start and pass it through the pipeline context.
- Update one adapter to read from `DUTInstance` instead of raw board config dict.

**Exit gate:** `rp2040_pico` pipeline run uses `DUTInstance`. Verified run passes.

---

### Phase 11: Deprecate Flat `mcu` Field

**Goal:** `_REQUIRED_FIELDS` no longer lists `mcu`. All manifests use `processors[]`.

Tasks:
- Remove `"mcu"` from `_REQUIRED_FIELDS`.
- Add `"processors"` to `_REQUIRED_FIELDS` with check for `processors[0].id`.
- Log a hard error (not just warning) when `mcu` is present without `processors`.
- Update `save_manifest()` in `assets.py` to write `processors` when saving new or promoted manifests.
- Update CLI `dut create` to prompt for processor list, not single MCU string.

**Exit gate:** No manifest in `assets_golden/duts/` has a bare `mcu` field. `find_golden_reference()` queries `processors[].id` only.

---

### Phase 12: Remove Two-File Redundancy

**Goal:** Board config (`configs/boards/<id>.yaml`) is formally referenced from the manifest or merged into it. No silent implicit file pair.

This is the most disruptive phase and should happen last. Options:

**Option A (Reference):** Add `board_config_ref: configs/boards/stm32g431cbu6.yaml` to the manifest. The loader reads both files and merges them. The board config file is kept but is now explicitly referenced.

**Option B (Merge):** Merge the board config fields directly into the manifest. A migration script generates the merged files. The board config files are archived or deleted.

**Recommendation:** Option A first (low risk, no file deletion), then Option B in a future version when all callers are confirmed stable.

**Exit gate:** `load_dut()` returns a fully merged board definition from a single call, regardless of which option is chosen.

---

## 6. Recommended Directory Evolution

Following the `ael/instruments/` pattern already established:

### Today

```
ael/
  assets.py                          # DUT loading, validation, find_golden_reference
  instruments/
    interfaces/
      base.py                        # InstrumentProvider (exists)
      registry.py                    # resolve_manifest_provider (exists)
    backends/
      stlink_backend/                # Exists
      esp32_jtag/                    # Exists

assets_golden/duts/<id>/manifest.yaml
configs/boards/<id>.yaml             # No formal link to manifest
```

### After Phase 2

```
ael/
  dut/                               # NEW
    __init__.py
    interfaces/
      __init__.py
      base.py                        # DUTProvider dataclass
      registry.py                    # resolve_dut_provider()
    backends/
      __init__.py
      manifest_adapter.py            # Wraps existing two-file model
    runtime/
      __init__.py
      dut_instance.py                # DUTInstance runtime class
```

### After Phase 12

```
assets_golden/duts/<id>/
  manifest.yaml                      # Unified: identity + board config merged
  docs.md
configs/processors/<mcu>.yaml        # Shared processor profiles
configs/boards/<id>.yaml             # Archived or referenced-only
```

---

## 7. Suggested Order of Technical Work

Ordered by risk level (lowest risk first):

| Order | Task | File(s) | Risk |
|---|---|---|---|
| 1 | Create `ael/dut/` skeleton (stubs only) | New files | Zero — nothing calls them |
| 2 | Create `manifest_adapter.py` backend | New file | Zero — wraps existing behavior |
| 3 | Update `assets.py` to accept `processors[]` alongside `mcu` | `ael/assets.py` | Low — additive change |
| 4 | Add `board_class` + `processors[]` to `rp2040_pico` manifest | `assets_golden/duts/rp2040_pico/manifest.yaml` | Low — no caller breaks |
| 5 | Add `capabilities` + `verification_profiles` to `rp2040_pico` board config | `configs/boards/rp2040_pico.yaml` | Low — additive keys |
| 6 | Route `default_verification.py` `rp2040_pico` worker through DUT registry | `ael/default_verification.py` | Medium — changes live path |
| 7 | Migrate remaining verified boards | Multiple manifests + board configs | Medium — multiple files |
| 8 | Create processor profiles in `configs/processors/` | New directory | Low — new files |
| 9 | Implement `DUTInstance` and use in pipeline | `ael/dut/runtime/dut_instance.py`, `ael/pipeline.py` | Medium |
| 10 | Remove `mcu` from `_REQUIRED_FIELDS` | `ael/assets.py` | High — breaks old manifests, do last |
| 11 | Merge or reference board configs from manifests | Multiple files | High — structural change |

---

## 8. Acceptance Gates

| Gate | Criterion | Verified by |
|---|---|---|
| A | `ael/dut/` imports without error | `python -c "import ael.dut"` |
| B | `manifest_adapter.py` wraps `rp2040_pico` correctly | Unit test: `load_board_definition("rp2040_pico")` returns valid DUTProvider |
| C | `_validate_manifest()` accepts both `mcu` and `processors[]` | Unit test: both schema variants pass |
| D | `rp2040_pico` default verification run passes with no regression | Full integration run |
| E | `stm32g431cbu6` default verification run passes with no regression | Full integration run |
| F | `find_golden_reference()` returns correct results for all 11 supported boards | Unit test: query by processor id and family |
| G | `list_duts()` returns all DUT assets as valid under new schema | `python -m ael dut list` |
| H | No manifest in `assets_golden/duts/` uses bare `mcu` field (Phase 11 only) | Schema validation script |

---

## 9. Verification Strategy During Migration

Use the existing verified worker matrix as the regression anchor. These boards must continue to pass their full verification runs at every phase:

| Board | Status | Build type | Flash method | Instrument |
|---|---|---|---|---|
| `stm32f103` | Verified | arm_debug | gdb_swd / bmda | stlink |
| `rp2040_pico` | Verified | pico | gdb_swd | esp32jtag |
| `stm32f411ceu6` | Likely verified | arm_debug | gdb_swd | stlink |
| `stm32h750vbt6` | Likely verified | arm_debug | bmda_gdbmi | stlink |
| `stm32g431cbu6` | Verified | arm_debug | bmda_gdbmi | esp32jtag |
| `esp32c6_devkit` | Not yet verified (pending_hw) | idf | idf_esptool | esp32jtag |

For phases that change `default_verification.py` or `pipeline.py`, run the full `stm32f103` + `rp2040_pico` matrix before merging. These two cover the widest range of adapters (stlink vs esp32jtag, cmake vs pico build system).

---

## 10. Compatibility Strategy

At every phase, maintain backwards compatibility with callers that use the old model:

1. **Keep `mcu` field in manifests** until Phase 11. Never remove it before all callers are migrated.
2. **Keep `verification_views` in board configs** until all callers read `verification_profiles` from the DUT registry.
3. **Keep `find_golden_reference()` scoring `mcu` field** until all manifests have `processors[]`.
4. **Keep direct dict access paths** in `pipeline.py` and `default_verification.py` as fallbacks until the new `DUTInstance` path is confirmed stable on all supported boards.
5. **Version the DUT schema** from Phase 4 onward. Old manifests without `schema_version` are treated as v0 and handled by the compatibility path.
6. **Do not change CLI behavior** (e.g., `ael dut list`, `ael dut create`) until the underlying data model changes are complete and tested.

---

## 11. Common Failure Modes to Avoid

| Failure mode | Description | Prevention |
|---|---|---|
| Big-bang file merge | Merging manifest + board config for all boards simultaneously | Do one board at a time; start with verified boards |
| Removing `mcu` too early | Deleting `mcu` before `processors[]` is everywhere causes `_REQUIRED_FIELDS` failures | Keep `mcu` as alias until Phase 11 |
| Breaking `find_golden_reference()` | Changing scoring logic causes wrong DUT selection for golden reference queries | Add unit tests before any changes to scoring logic |
| Forgetting orphaned board configs | `configs/boards/<id>.yaml` files without manifests continue to be used but are not tracked | Phase 9 specifically addresses this; do not skip it |
| Coupling `DUTInstance` to `pipeline.py` too tightly | If `DUTInstance` becomes mandatory too early, boards not yet migrated break | Keep DUTInstance optional in pipeline until all boards are migrated |
| Silently ignoring the two-file boundary | Writing code that assumes a merged model exists before Phase 12 | All new code must handle the two-file case explicitly until Phase 12 |

---

## 12. Guardrails

These guardrails must hold throughout the migration:

1. **Never break a verified run.** A phase is not complete until all verified boards pass their full verification run. Partial migration of one board must not affect others.

2. **Never silently drop data.** When reading an old manifest format (flat `mcu`), the compatibility path must log the format version and emit a deprecation warning — it must never silently ignore the old field.

3. **Never write runtime state to static definitions.** `DUTInstance` fields (bound instrument, session ID, current status) must never be written back to `manifest.yaml` or board config files.

4. **Keep the interface surface minimal.** `DUTProvider` should not expose methods that exist only for internal implementation reasons. Every method in the interface must have at least one concrete caller.

5. **Processor profiles are read-only references.** Board definitions reference processor profiles by ID; they do not embed or override processor profile content. If a board needs a processor variant not in the profile library, add a new profile.

6. **Board configs remain valid yaml.** Even after being referenced from manifests, `configs/boards/<id>.yaml` files must remain valid standalone YAML that can be loaded independently. This preserves backwards compatibility with any external tooling that reads them directly.

---

## 13. First Concrete Coding Moves

These are the first five concrete changes to make. Each is independent and low-risk.

### Move 1: Create `ael/dut/interfaces/base.py`

```python
# ael/dut/interfaces/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict

@dataclass(frozen=True)
class DUTProvider:
    board_class: str
    identify: Callable[[Dict[str, Any]], Dict[str, Any]]
    get_capabilities: Callable[[Dict[str, Any]], Dict[str, Any]]
    get_verification_profiles: Callable[[Dict[str, Any]], Dict[str, Any]]
    list_processors: Callable[[Dict[str, Any]], list]
    doctor: Callable[[Dict[str, Any]], Dict[str, Any]]
```

**File to create:** `ael/dut/interfaces/base.py`
**Existing analog:** `ael/instruments/interfaces/base.py` (`InstrumentProvider`)

---

### Move 2: Create `ael/dut/interfaces/registry.py`

```python
# ael/dut/interfaces/registry.py
from __future__ import annotations
from typing import Any, Dict, Optional
from ael.dut.interfaces.base import DUTProvider

def resolve_dut_provider(board_id: str) -> Optional[DUTProvider]:
    # Phase 1: returns None for all inputs (stub)
    # Phase 2: returns manifest_adapter provider
    return None

def load_board_definition(board_id: str) -> Optional[Dict[str, Any]]:
    # Load and merge manifest.yaml + board config dict
    # Phase 2: implement by calling manifest_adapter
    return None
```

**File to create:** `ael/dut/interfaces/registry.py`
**Existing analog:** `ael/instruments/interfaces/registry.py`

---

### Move 3: Migrate `assets.py` `_REQUIRED_FIELDS` to accept `processors[]`

Change in `ael/assets.py`:

```python
# Before:
_REQUIRED_FIELDS = [
    "id",
    "mcu",
    "family",
    ...
]

# After (transition):
_REQUIRED_FIELDS = [
    "id",
    "family",       # keep for now; remove in Phase 11
    "description",
    ("build", "type"),
    ("build", "project_dir"),
    ("flash", "method"),
    ("verified", "status"),
]
# processors[] or mcu accepted — validated in _validate_manifest() with deprecation warning
```

**File to modify:** `ael/assets.py`

---

### Move 4: Create `ael/dut/runtime/dut_instance.py`

```python
# ael/dut/runtime/dut_instance.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class DUTInstance:
    board_id: str
    board_def: Dict[str, Any]
    instrument_instance: Optional[str] = None
    session_id: Optional[str] = None
    status: str = "idle"   # idle | flashing | verifying | error
    runtime_data: Dict[str, Any] = field(default_factory=dict)
```

**File to create:** `ael/dut/runtime/dut_instance.py`

---

### Move 5: Convert one `default_verification` worker path to go through DUT registry

In `ael/default_verification.py`, locate the worker setup for `rp2040_pico` (or the generic worker setup that loads board config). Add a DUT registry lookup before the existing dict access:

```python
# Near top of worker setup, before existing board config dict access:
from ael.dut.interfaces import registry as dut_registry

provider = dut_registry.resolve_dut_provider(board_id)
if provider is not None:
    verification_profiles = provider.get_verification_profiles(board_def)
else:
    # Fallback: use old verification_views from board config dict
    verification_profiles = (board_cfg.get("board") or {}).get("verification_views", {})
```

**File to modify:** `ael/default_verification.py`

---

## 14. What "Done" Should Mean

The migration is done when the following are all true:

- [ ] `ael/dut/` exists with `interfaces/`, `backends/`, and `runtime/` subdirectories.
- [ ] `DUTProvider` is implemented for all boards in `assets_golden/duts/`.
- [ ] Every manifest in `assets_golden/duts/` has `board_class`, `processors[]`, `capabilities`, and `verification_profiles`.
- [ ] No manifest in `assets_golden/duts/` has a bare `mcu` string field as its only processor identifier.
- [ ] `assets.py` `_REQUIRED_FIELDS` requires `processors[0].id`, not `mcu`.
- [ ] `find_golden_reference()` queries `processors[].id` and `processors[].family`.
- [ ] `default_verification.py` worker setup uses `DUTInstance` for all boards.
- [ ] `pipeline.py` passes `DUTInstance` through the run context.
- [ ] All boards with `verified.status: true` continue to pass their full verification runs.
- [ ] `configs/boards/<id>.yaml` files are either merged into manifests or explicitly referenced.
- [ ] A new board can be onboarded by creating a single manifest file and a processor profile reference, without creating a separate board config file.

---

## 15. Final Recommendation

Start with Moves 1–4 in Section 13. These four moves create the interface skeleton, update the schema validation, and add the runtime class. They touch no active execution paths and have zero regression risk.

Then do Move 5 to route the `rp2040_pico` `default_verification` path through the new registry. This is the first real test that the interface layer works.

Then migrate `rp2040_pico` manifest and board config to the unified schema (Phase 4). Run the full `rp2040_pico` verification. If it passes, the migration pattern is proven.

At that point, the remaining boards follow the same pattern with confidence.

Do not touch `mcu` removal (Phase 11) or the board config merge (Phase 12) until all other phases are complete and stable.

---

## 16. Codebase-Specific Notes

These are specific observations about the current code that shaped this plan.

### `assets.py` validation is minimal and dict-based

`_validate_manifest()` checks for presence of keys in a plain dict. There is no schema library (no pydantic, no jsonschema). Any new fields added to `_REQUIRED_FIELDS` must be handled by the same hand-written key-traversal logic. The nested field check uses tuple syntax: `("build", "type")` checks `manifest["build"]["type"]`. The `processors[]` migration will require adding a new check type for indexed list access.

### `find_golden_reference()` scoring is fragile for multi-board MCU families

The 100-point MCU match assumes `mcu` uniquely identifies the right board. For `stm32f103` family, multiple boards (`stm32f103`, `stm32f103_gpio`, `stm32f103_uart`) share the same MCU. The current scoring differentiates them only by tag intersection (5 pts/tag). This is already breaking for the existing board set and will get worse as more variants are added.

### `configs/boards/` has more entries than `assets_golden/duts/`

There are board config files for boards that have no DUT manifest: `stm32f030c8t6`, `stm32f407_discovery`, draft configs for `stm32f401ce` and `stm32f407vg`. These boards are operationally supported (board configs exist, presumably used) but are invisible to `list_duts()` and `find_golden_reference()`. Phase 9 must address this gap before the two-file merge is attempted, or boards will be silently excluded from the registry.

### `default_verification.py` imports from `pipeline.py` internals

`from ael.pipeline import _extract_verify_result_details, _normalize_probe_cfg, _simple_yaml_load, run_pipeline`

Three of these four imports use leading-underscore private names from `pipeline.py`. This is a coupling that will make it harder to route `default_verification.py` through a new DUT interface without also touching `pipeline.py`. When Move 5 is implemented, keep the initial change minimal and do not attempt to also refactor the `pipeline.py` coupling in the same commit.

### `verification_model.py` already has `dut_ids` in resource key parsing

In `ael/verification_model.py`, `summarize_resource_keys()` already handles `"dut:"` prefixed resource keys and puts them in `summary["dut_ids"]`. This means DUT-level resource locking is at least partially anticipated in the model. `DUTInstance` should integrate with this existing resource key scheme rather than inventing a new one.

### The instrument interface pattern is the right model

`ael/instruments/interfaces/stlink.py` demonstrates the full pattern: `native_interface_profile()`, `identify()`, `get_capabilities()`, `get_status()`, `doctor()`, and a `PROVIDER` singleton. The DUT interface should follow this exact structure. The `InstrumentProvider` dataclass in `ael/instruments/interfaces/base.py` is 47 lines. The `DUTProvider` dataclass should be similarly concise.

### Board configs use `board:` top-level key; manifests use no top-level key

`configs/boards/stm32g431cbu6.yaml` wraps everything under a `board:` key. `assets_golden/duts/esp32c6_devkit/manifest.yaml` uses flat top-level keys with no wrapper. Any code that merges the two files must strip the `board:` wrapper from board config content before merging, or use the `board.` prefix explicitly when accessing board config fields.
