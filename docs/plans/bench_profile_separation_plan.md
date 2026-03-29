# Plan: Separate Bench Wiring from Board Identity

**Date:** 2026-03-29
**Status:** Approved, not yet started
**Priority:** Must complete before stm32f401rct6 stage3 pack is created

---

## Background & Why This Change Is Needed

### The Problem

Every board config file (e.g. `configs/boards/stm32f401rct6.yaml`) currently contains two fundamentally different kinds of information mixed together:

**Invariant identity fields** — things that are true about the MCU regardless of how it is wired:
- MCU target name, clock speed
- Instrument instance and endpoint
- SWD/reset/power settings
- Build and flash configuration

**Variable bench wiring fields** — things that describe how this specific bench is physically wired for a specific test setup:
- `bench_connections` — physical wire map (e.g. `PA2 → P0.0`, `PA3 → P0.1`)
- `observe_map` — logical name → instrument pin aliases
- `verification_views` — named signal views used in evidence capture
- `default_wiring` — which instrument channel is used for verify/reset
- `safe_pins` — which MCU pins are safe to connect probes to

Because these are all in one file, `board_id` implies a single fixed wiring. This works fine when you have exactly one physical board with one fixed wiring. It breaks down in the following real scenarios:

**Scenario A — Same MCU, different test suites with different wiring**

`stm32f401rct6` currently has:
- `stm32f401rct6_stage0` / `stage0_mailbox` / `stage1` — no external wiring needed beyond SWD
- `stm32f401rct6_stage3` (planned) — needs PA8↔PA6, PA9↔PA10, PB0↔PB1, LA probes on P0.0/P0.1/P0.2

Both stages use the same MCU and the same instrument. The `bench_connections` in the current board config describe the fully-wired setup. If you run stage0/1 with those connections listed, the runner generates warnings about pins that are declared but not physically connected. If you remove them for stage0/1, stage3 breaks.

**Scenario B — Same MCU, multiple physical boards on different benches**

If you have two `stm32f401rct6` boards — one on a minimal SWD-only bench and one on a fully-wired bench — they need different `bench_connections` but they are the same MCU. Today there is no way to express this without creating a second board_id like `stm32f401rct6_bench2` which pollutes the board namespace and suggests a different MCU when it is the same chip.

**Scenario C — Reusing wiring across boards**

Some wiring patterns (e.g. a loopback jumper setup) are shared across multiple board families. There is currently no way to share or reference a wiring template — each board config duplicates it.

### What the Current Code Does

`pipeline.py` resolves `configs/boards/{board_id}.yaml` → a flat dict `board_raw`. This is passed to `strategy_resolver.resolve_run_strategy()` which builds `board_cfg`. Then `connection_model.normalize_connection_context()` reads `board_cfg.get("bench_connections")`, `board_cfg.get("observe_map")`, and `board_cfg.get("verification_views")` to build the wiring context used throughout the run.

The pack JSON today only has a `board` field — it cannot influence which wiring is loaded. The wiring is always whatever is in the board config file.

---

## The Fix: Bench Profiles

### Core Idea

Extract the variable wiring fields into a separate file called a **bench profile**. Board configs keep only the invariant MCU identity fields. Packs can optionally specify which bench profile to use — and if they don't, a sensible default is used automatically.

```
configs/boards/{board_id}.yaml        ← MCU identity only (invariant)
configs/bench_profiles/{id}.yaml      ← bench wiring (swappable per suite)
packs/{name}.json                     ← optionally: "bench_profile": "{id}"
```

### New Directory and File Format

**Location:** `configs/bench_profiles/`

**Naming convention:** `{board_id}__{profile_name}.yaml` (double underscore separates board scope from profile name)

Examples:
- `configs/bench_profiles/stm32f401rct6__default.yaml` — current full wiring
- `configs/bench_profiles/stm32f401rct6__stage3.yaml` — future wiring for banner tests
- `configs/bench_profiles/stm32f401rct6__swd_only.yaml` — minimal bench, SWD only

**Bench profile file schema:**

```yaml
bench_profile:
  id: stm32f401rct6__default
  board_id: stm32f401rct6
  description: "GPIO waveform wiring: PA2→P0.0, PA3→P0.1, PB13→P0.2, PC13→LED"

  bench_connections:
    - from: PA2
      to: P0.0
    - from: PA3
      to: P0.1
    - from: PB13
      to: P0.2
    - from: PC13
      to: LED
    - from: PC13
      to: P0.3
    - from: GND
      to: probe GND

  observe_map:
    sig: P0.0
    pa2: P0.0
    pa3: P0.1
    pb13: P0.2
    led: LED

  verification_views:
    signal:
      pin: sig
      resolved_to: P0.0
      description: Primary proof capture on PA2
    aux:
      pin: pb13
      resolved_to: P0.2
      description: Auxiliary SPI clock pin on PB13

  default_wiring:
    swd: "P3"
    reset: "NC"
    verify: "P0.0"

  safe_pins:
    - PA2
    - PA3
    - PA8
    - PA9
    - PA10
    - PB0
    - PB1
    - PB13
    - PB14
    - PB15
    - PC13
```

### Changes to Board Config Format

Fields **removed** from board config (move to bench profile):
- `bench_connections`
- `observe_map`
- `verification_views`
- `default_wiring`
- `safe_pins`

Field **added** to board config:
```yaml
board:
  ...
  default_bench_profile: stm32f401rct6__default   # optional; stem of file in configs/bench_profiles/
```

Board config after migration (only invariant identity remains):
```yaml
board:
  name: STM32F401RCT6
  target: stm32f401rct6
  instrument_instance: esp32jtag_blackpill_192_168_2_106
  clock_hz: 16000000
  default_bench_profile: stm32f401rct6__default
  build:
    type: arm_debug
    project_dir: firmware/targets/stm32f401rct6
    artifact_stem: stm32f401_app
  flash:
    speed_khz: 1000
    reset_strategy: connect_under_reset
    post_load_settle_s: 5.0
    target_id: 1
    gdb_launch_cmds:
      - "file {firmware}"
      - "monitor a"
      - "attach {target_id}"
      - "load"
      - "attach {target_id}"
      - "detach"
  power_and_boot:
    reset_strategy: connect_under_reset
    boot_mode_default: normal
    power_rails:
      - name: VDD
        nominal_v: 3.3
```

### How Packs Reference Bench Profiles

Add an optional `bench_profile` field to pack JSON:

```json
{
  "name": "stm32f401rct6_stage3",
  "board": "stm32f401rct6",
  "bench_profile": "stm32f401rct6__stage3",
  "tests": [...]
}
```

If `bench_profile` is absent from the pack, the runner uses the board config's `default_bench_profile`. If that is also absent, it falls back to inline fields in the board config (full backwards compatibility).

---

## Implementation: "Wide, Not Deep"

This was described this way deliberately. The change is:

- **Not deep** — the actual new logic is small. One new module of ~80 lines. One merge step in one existing function. No new concepts in the pipeline, no new stage types, no protocol changes.
- **Wide** — it touches many files because 20 board configs need to be migrated, and `pack_meta` needs to be threaded through 4–5 call sites in the pipeline.

The width is mostly mechanical (copy-paste extraction of fields into new files). The depth is contained to one injection point in `strategy_resolver.py`.

**Risk level: Low.** Backwards compatibility is guaranteed by a three-tier fallback:
1. Explicit bench profile in pack JSON
2. `default_bench_profile` in board config
3. Inline bench fields in board config (current behavior — always fires until you explicitly extract)

Nothing breaks until you deliberately remove inline fields from a board config.

---

## Implementation Steps

### Phase 0 — Infrastructure only (no behavior change)

**Step 1:** Create `configs/bench_profiles/` directory.

**Step 2:** Create `ael/bench_profile_loader.py` with three functions:

```python
def resolve_bench_profile_id(board_raw: dict, pack_meta: dict | None = None) -> str | None:
    """
    Returns the bench profile id to load.
    Priority: pack_meta["bench_profile"] > board_raw["board"]["default_bench_profile"] > None
    """

def load_bench_profile(repo_root: str, profile_id: str) -> dict:
    """
    Loads configs/bench_profiles/{profile_id}.yaml.
    Returns the dict under the top-level "bench_profile" key.
    Raises FileNotFoundError if not found.
    """

def resolve_bench_wiring_fields(
    repo_root: str,
    board_raw: dict,
    pack_meta: dict | None = None,
) -> dict:
    """
    Returns a dict with keys: bench_connections, observe_map,
    verification_views, default_wiring, safe_pins.

    Resolution order:
    1. If bench_profile_id resolves → load profile file → return its fields.
    2. Else if board_raw["board"] has inline wiring fields → return those.
    3. Else return empty dict.
    """
```

**Step 3:** Add `validate_bench_profile(profile: dict)` to `ael/connection_metadata.py` — reuses existing field validators (`validate_bench_connections`, `validate_observe_map`, etc.) applied to the `bench_profile:` dict from the YAML.

At end of Phase 0: no behavior changes, new module exists but is not called anywhere yet.

---

### Phase 1 — Wire into execution path (still no behavior change)

**Step 4:** Modify `ael/strategy_resolver.py`:
- Add optional `pack_meta: dict | None = None` parameter to `resolve_run_strategy()`.
- After building `board_cfg` from `board_raw`, add:
  ```python
  from ael.bench_profile_loader import resolve_bench_wiring_fields
  bench_fields = resolve_bench_wiring_fields(str(repo_root), board_raw, pack_meta=pack_meta)
  board_cfg.update(bench_fields)
  ```

**Step 5:** Modify `ael/pipeline.py`:
- In `run_pipeline()`, construct `pack_meta = {"bench_profile": pack.get("bench_profile")}` from the pack dict and thread it to `resolve_run_strategy()`.
- In `run_pack()`, pass `bench_profile` from the pack JSON into the `pack_meta` dict.

**Step 6:** Modify `ael/__main__.py` `run_pack()` entry point — pass `bench_profile` from the loaded pack JSON into `pack_meta`.

**Step 7:** Minor update to `ael/stage_explain.py` — thread `pack_meta` to `resolve_run_strategy()` if it calls it directly.

At end of Phase 1: system behaves identically to before (Tier 3 inline fallback fires every time since no profiles exist yet).

**Verification:** Run `stm32f401rct6_stage0`, `stm32f401rct6_stage1`, and `smoke_stm32f401` packs and confirm all pass with identical output to before.

---

### Phase 2 — Migrate board configs (priority order)

For each board config, the mechanical steps are:

```
a. Create configs/bench_profiles/{board_id}__default.yaml
   (extract bench_connections, observe_map, verification_views,
    default_wiring, safe_pins from the board config)

b. Add  default_bench_profile: {board_id}__default  to board config's board: section

c. Remove the extracted fields from the board config

d. Run the relevant pack to confirm no regression
```

**Migration order:**

| Order | Board | Reason |
|-------|-------|--------|
| 1 | `stm32f401rct6` | Active focus; blocks stage3 work |
| 2 | `stm32f411ceu6` | Golden, active |
| 3 | `stm32f103_gpio` | Golden, active |
| 4 | `stm32g431cbu6` | Golden, most mature |
| 5 | `stm32f401ce_blackpill` | Active development |
| 6 | `stm32f407_discovery` | Golden |
| 7 | `stm32h750vbt6` | Golden |
| 8–20 | Remaining boards | Can be done lazily over time |

After migrating `stm32f401rct6` (order 1), stage3 work can proceed. The remaining boards can be migrated in subsequent sessions.

---

### Phase 3 — Prove multi-profile (the whole point)

**Step 8:** Create `configs/bench_profiles/stm32f401rct6__stage3.yaml` with the wiring needed for the banner tests:
- PA8 ↔ PA6 (GPIO/EXTI/capture/PWM loopback)
- PA9 ↔ PA10 (UART loopback)
- PB0 ↔ PB1 (ADC loopback)
- PA2 → P0.0, PA3 → P0.1, PB13 → P0.2 (LA capture)

**Step 9:** Create `packs/stm32f401rct6_stage3.json` with `"bench_profile": "stm32f401rct6__stage3"`.

**Step 10:** Run stage3 pack and confirm it loads the correct wiring context automatically.

---

## File Touch-point Summary

| File | Change type | Description |
|------|-------------|-------------|
| `ael/bench_profile_loader.py` | **New file** | ~80 lines; all load/resolve/fallback logic |
| `configs/bench_profiles/*.yaml` | **New files** | One per board per profile; ~20 initially |
| `ael/strategy_resolver.py` | **Modified** | Accept `pack_meta`; merge bench fields after building `board_cfg` |
| `ael/pipeline.py` | **Modified** | Thread `pack_meta` (with `bench_profile`) to `resolve_run_strategy` |
| `ael/__main__.py` | **Modified** | Pass `bench_profile` from pack JSON into `pack_meta` |
| `ael/stage_explain.py` | **Minor** | Thread `pack_meta` to `resolve_run_strategy` |
| `ael/connection_metadata.py` | **Modified** | Add `validate_bench_profile()` |
| `configs/boards/*.yaml` (20 files) | **Modified** | Remove wiring fields; add `default_bench_profile` |
| `ael/connection_model.py` | **No change** | Already reads from `board_cfg` dict; works once dict is populated |
| `ael/config_resolver.py` | **No change** | Identity-only resolution; no wiring logic |
| `ael/connection_doctor.py` | **No change** | Reads from `connection_setup`, not board raw |
| `packs/*.json` | **Optional** | Add `bench_profile` field only to packs needing non-default wiring |

---

## What NOT to Change

- `ael/connection_model.py` — already reads from `board_cfg` dict; once the dict is properly populated upstream, this works with zero changes.
- `ael/config_resolver.py` — pure instrument/identity resolution; no wiring logic here.
- Test plan JSON files — bench wiring is a pack/board concern, not a per-test concern.
- `assets_golden/duts/*/manifest.yaml` — `board_configs` entries do not need to change; bench profile is resolved at runtime, not encoded in the manifest.

---

## Recommended Starting Approach for a New Session

1. Read this document fully.
2. Read these files to understand current code before touching anything:
   - `ael/strategy_resolver.py` — find `resolve_run_strategy()`; this is where the merge step goes
   - `ael/pipeline.py` — find `run_pipeline()` and `run_pack()`; understand how `pack_meta` can be threaded
   - `ael/__main__.py` — find the `pack` subcommand handler
   - `ael/connection_model.py` — see `normalize_connection_context()`; understand it just reads from `board_cfg`
   - `configs/boards/stm32f401rct6.yaml` — the primary migration target; see exactly what fields exist
3. Implement Phase 0 first (new module + validation only). No calls to it yet.
4. Implement Phase 1 (wire it in). Run existing packs to confirm zero regression before proceeding.
5. Migrate `stm32f401rct6` (Phase 2, board 1). Run its packs to confirm.
6. Create `stm32f401rct6__stage3` profile and pack (Phase 3). This is the deliverable that unblocks stage3 test work.

---

## Commit Strategy

Each step should be a separate commit:

```
feat: add bench_profile_loader module (Phase 0)
feat: wire bench profile loading into pipeline (Phase 1)
feat: migrate stm32f401rct6 to bench profile (Phase 2 - board 1)
feat: add stm32f401rct6__stage3 bench profile and pack (Phase 3)
feat: migrate stm32f411ceu6 to bench profile (Phase 2 - board 2)
...
```

This keeps each commit independently revertable and makes the PR review straightforward.

---

*Plan authored: 2026-03-29. Context: stm32f401rct6 stage3 work blocked on this architectural issue. Discovered during bench wiring review for the banner test suite.*
