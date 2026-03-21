# DUT Standardization Specification v0.1

**Status:** Draft
**Date:** 2026-03-21
**Scope:** ai-embedded-lab (`ael/`) codebase

---

## 1. Purpose

This specification defines the canonical model for a Device Under Test (DUT) in the AEL (AI Embedded Lab) platform. It establishes how DUTs are described, classified, validated, and accessed at runtime.

The goals of this specification are to:

- Give DUT a first-class, board-first identity model.
- Separate static DUT definition from runtime execution state.
- Provide a unified, versioned interface that replaces direct dict access to manifest and board config fields.
- Enable capability-driven dispatch so pack and pipeline logic does not hard-code board-specific behavior.
- Establish a migration path from the current two-file design (manifest + board config) to a single unified DUT model.

---

## 2. Core Decision: Board-First Identity

**The board is the canonical identity anchor for a DUT.**

A DUT in AEL is identified by its board ID (e.g., `rp2040_pico`, `stm32g431cbu6`). The board uniquely determines:

- Which processor(s) are present and how to access them.
- What build toolchain and flash method to use.
- What physical connections the board presents.
- What verification expectations are defined.

### Rationale

| Alternative considered | Why rejected |
|---|---|
| MCU-first identity | Multiple boards use the same MCU; `find_golden_reference()` already shows MCU queries are ambiguous |
| Test-plan-first identity | Test plans are ephemeral; boards are stable assets |
| Bench-first identity | Bench topology is lab-specific and changes across deployments |

A board-first approach is the only identity model that is stable across labs, reusable across test plans, and maps cleanly to the existing `assets_golden/duts/<id>/` directory structure.

---

## 3. Design Principles

### 3.1 Board-First

Every DUT is anchored to a board identity. The board defines what the DUT is; the processor profile describes what it contains.

### 3.2 MCU-Backed Reuse

Processor profiles (MCU, family, core architecture) are defined once and referenced by boards. Boards do not duplicate processor metadata; they reference it. This makes adding a new variant of an existing MCU cheap.

### 3.3 One Model for All DUTs

Standard devkits, custom boards, and multi-processor composite boards all use the same model structure. The `board_class` field (`standard`, `special`, `composite`) adjusts validation and composition rules without requiring a separate model.

### 3.4 Explicit Composition

Multi-processor boards explicitly list each processor as a separate entry in `processors[]`. There is no implicit "primary processor" assumption unless explicitly flagged in the list.

### 3.5 Runtime Separation

The static DUT definition (files on disk) is separate from runtime state (current job, bound instrument, test session). Runtime state is never written back to the static definition file.

### 3.6 Capability-Driven Dispatch

Pack steps and pipeline stages select flash method, verify strategy, and build adapter based on declared `capabilities`, not by switching on `mcu` or `family` strings. This is the same pattern already used in `ael/instruments/` where backend selection is driven by capability declarations.

---

## 4. DUT Model Layers

The DUT model has three explicit layers. Each layer has a distinct lifecycle and storage location.

### Layer 1: Processor Profile

Reusable, MCU-level metadata. Defined once per MCU variant. Referenced by boards.

**Examples:** `esp32c6`, `rp2040`, `stm32g431cbu6`, `stm32h750vbt6`

**Proposed location:** `configs/processors/<mcu_id>.yaml`

### Layer 2: Board Definition

The DUT static asset. Combines processor reference(s), build/flash policy, wiring layout, and verification declarations. This is the primary artifact managed under `assets_golden/duts/<id>/`.

**Current state:** Split across two files:
- `assets_golden/duts/<id>/manifest.yaml` — identity, build, flash, tags, verified status
- `configs/boards/<id>.yaml` — instrument binding, observe map, verification views, bench connections, power/boot policy

**Target state:** A single unified DUT definition that merges these concerns, with the board config fields either inlined or referenced by stable ID.

### Layer 3: Runtime Instance

A transient, in-memory object created when a run is scheduled. Holds bound instrument, resolved config, session ID, and current status. Never persisted to the static definition.

**Current state:** Does not formally exist. Runtime code passes dicts (manifest + probe config) directly to adapters and pipeline steps. The `ael/dut/` directory does not exist.

**Target state:** A `DUTInstance` class in `ael/dut/runtime/dut_instance.py`.

---

## 5. DUT Taxonomy

Every board definition must declare a `board_class`.

| Class | Meaning | Example |
|---|---|---|
| `standard` | Single processor, standard devkit or evaluation board | `rp2040_pico`, `esp32c6_devkit` |
| `special` | Single processor, custom or non-standard board requiring additional setup steps | Custom STM32 bench target with non-default reset strategy |
| `composite` | Multiple processors or heterogeneous core architecture | Dual-core ESP32S3 with explicit core targeting, future RP2350 dual-core usage |

Validation rules:
- `standard`: `processors[]` must have exactly one entry; `capabilities` must be non-empty.
- `special`: `processors[]` must have exactly one entry; must include a `notes` field explaining the special handling.
- `composite`: `processors[]` must have two or more entries; each must declare its role (`primary`, `secondary`, `dsp`, etc.).

---

## 6. Required Board Definition Fields

### Current State (Two Files)

**`assets_golden/duts/<id>/manifest.yaml`** (currently required by `assets.py` `_REQUIRED_FIELDS`):

| Field | Type | Notes |
|---|---|---|
| `id` | string | Board identifier |
| `mcu` | string | **Single MCU string — must migrate to `processors[]`** |
| `family` | string | MCU family |
| `description` | string | Human-readable description |
| `build.type` | string | Build adapter type |
| `build.project_dir` | string | Path to firmware project |
| `flash.method` | string | Flash adapter key |
| `verified.status` | bool | Verification gate |

**`configs/boards/<id>.yaml`** (currently required by pipeline/board config resolution):

| Field | Type | Notes |
|---|---|---|
| `board.name` | string | Display name |
| `board.target` | string | Toolchain target string |
| `board.instrument_instance` | string | Bound instrument ID |
| `board.build` | dict | Build config (type, project_dir, artifact_stem) |
| `board.flash` | dict | Flash config (speed, reset strategy) |
| `board.observe_map` | dict | Signal alias to probe channel mapping |
| `board.verification_views` | dict | Named verification scenarios |
| `board.bench_connections` | list | Physical wiring declarations |
| `board.default_wiring` | dict | Default SWD, reset, verify pin assignments |
| `board.power_and_boot` | dict | Reset strategy and power rail declarations |

### Target State (Unified Board Definition)

After migration, a board definition must contain all required fields. Required fields for the unified schema:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | Yes | Stable board identifier |
| `board_class` | string | Yes | `standard`, `special`, or `composite` |
| `name` | string | Yes | Human-readable board name |
| `processors` | list | Yes | **Replaces `mcu` single-string field** |
| `processors[].id` | string | Yes | MCU identifier (e.g., `esp32c6`) |
| `processors[].family` | string | Yes | MCU family |
| `processors[].role` | string | Yes for composite | `primary`, `secondary`, etc. |
| `description` | string | Yes | Purpose and behavior |
| `capabilities` | list | Yes | Declared capability tokens |
| `build` | dict | Yes | `type`, `project_dir` |
| `flash` | dict | Yes | `method` |
| `observe_map` | dict | Conditional | Required if any verification uses GPIO |
| `verification_profiles` | dict | Yes | Named verification scenarios (formalizes current `verification_views`) |
| `bench_connections` | list | Conditional | Required for `standard` and `composite` |
| `default_wiring` | dict | Conditional | Required if SWD/reset wiring is non-trivial |
| `power_and_boot` | dict | Yes | Reset strategy, boot mode, power rails |
| `connection_profiles` | dict | No | Optional named wiring variants |
| `tags` | list | No | Searchable tags |
| `verified` | dict | Yes | `status`, `date`, `bench_id` |

### Migration Note on `mcu`

`assets.py` currently requires `mcu` as a top-level string field. This must be migrated:

- Add `processors[]` as the canonical source.
- Retain `mcu` as a deprecated compatibility alias during transition.
- Update `_REQUIRED_FIELDS` to require `processors[0].id` instead of `mcu`.
- Update `find_golden_reference()` to query against `processors[].id` and `processors[].family` instead of the flat `mcu` and `family` fields.

---

## 7. Processor Profile Requirements

A processor profile describes a single MCU variant. It is a shared resource; multiple boards can reference the same profile.

Required fields in a processor profile:

| Field | Type | Notes |
|---|---|---|
| `id` | string | MCU identifier, must be unique across all profiles |
| `family` | string | MCU family (e.g., `esp32`, `stm32`, `rp2040`) |
| `architecture` | string | Core architecture (e.g., `rv32imac`, `cortex-m4`, `cortex-m0+`) |
| `cores` | list | List of core descriptors (id, architecture, count) |
| `flash_method_hints` | list | Suggested flash methods for this MCU |
| `debug_interface` | string | Primary debug interface (e.g., `swd`, `jtag`, `uart_boot`) |
| `toolchain_target` | string | Default toolchain target string |

---

## 8. Bare MCU / SoC Handling

Some DUTs are bare SoCs mounted on a minimal carrier, not standard devkits. These are modeled as `board_class: special` boards with:

- A complete board definition (all required fields).
- A `notes` field documenting what is non-standard.
- `connection_profiles` entries for any wiring variants that differ from the default bench layout.
- Power rail declarations that reflect the actual carrier, not assumed devkit defaults.

Bare SoC boards must not skip `bench_connections` or `observe_map` fields by defaulting to the processor profile. The board definition must be explicit.

---

## 9. Multi-Processor Handling

Boards with multiple processors use `board_class: composite` and declare each processor explicitly in `processors[]`.

```yaml
board_class: composite
processors:
  - id: rp2350_arm
    family: rp2350
    architecture: cortex-m33
    role: primary
    debug_interface: swd
  - id: rp2350_riscv
    family: rp2350
    architecture: rv32imac
    role: secondary
    debug_interface: swd
```

Rules for composite boards:

1. Each processor must declare a `role`.
2. `capabilities` must declare which processor each capability belongs to using `processor_role` annotations where ambiguous.
3. `observe_map` entries may optionally carry a `processor` annotation.
4. Build and flash configuration must specify which processor context each applies to.

**Current state:** No composite boards exist in the repo today. `rp2350_pico2` is currently defined with `board_class` absent and a single `mcu` field. It should be the first candidate for composite board modeling when the spec is implemented.

---

## 10. Separation of Static vs Runtime Data

### Static Data (on disk)

Static DUT data describes what the board is. It changes only when the board definition changes (new firmware behavior, new wiring, promotion status update). Static data lives in:

- `assets_golden/duts/<id>/manifest.yaml` — golden, read-only source of truth
- `assets_user/duts/<id>/manifest.yaml` — user-local overrides or in-progress work
- `configs/boards/<id>.yaml` — board execution policy (currently separate, target: merged with manifest)

**Note:** Currently, `assets_golden/duts/` holds only the manifest half of the board definition. The other half (wiring, observe map, verification views, instrument binding) lives in `configs/boards/`. These two files must eventually be unified into a single board definition file, or the board config must be formally referenced from the manifest.

### Runtime Data (in memory only)

Runtime data describes the current execution context for a DUT. It is created when a run starts and discarded when the run ends. It must never be written back to the static definition.

Runtime data includes:

- Bound instrument instance (resolved from `board.instrument_instance` or explicit override)
- Current job/run ID
- Active test plan
- Live status (flashing, verifying, idle)
- Session-scoped resource locks

**Current state:** No formal runtime home. Runtime code uses raw dicts passed between `pipeline.py`, `default_verification.py`, and adapter functions. The target is a `DUTInstance` class in `ael/dut/runtime/dut_instance.py`.

---

## 11. Standard DUT Interface

**Current state:** This interface does not exist. Code that needs DUT information reads directly from the manifest dict or the board config dict using plain key access (e.g., `manifest.get("mcu")`, `board.get("observe_map")`). There is no Python class representing a DUT, no method to call, and no registry to look up DUTs from.

The instrument layer (`ael/instruments/interfaces/`) provides the pattern to follow. Each instrument family implements an `InstrumentProvider` dataclass with a fixed set of callable fields: `identify`, `get_capabilities`, `get_status`, `doctor`, and `actions`. The DUT interface should follow the same pattern.

### Target: `DUTProvider` Interface

Analogous to `InstrumentProvider` in `ael/instruments/interfaces/base.py`, a `DUTProvider` should expose:

| Method | Signature | Description |
|---|---|---|
| `identify` | `(board_def: dict) -> dict` | Return stable identity: id, board_class, processors, family |
| `get_identity` | `(board_def: dict) -> dict` | Alias for `identify`; intended for runtime use |
| `get_status` | `(instance: DUTInstance) -> dict` | Return current runtime status of the DUT |
| `get_capabilities` | `(board_def: dict) -> dict` | Return declared capabilities as a structured dict |
| `get_verification_profiles` | `(board_def: dict) -> dict` | Return named verification scenarios |
| `get_connection_profile` | `(board_def: dict, name: str) -> dict` | Return a named wiring profile |
| `doctor` | `(instance: DUTInstance) -> dict` | Check DUT health (power, connectivity, probe reachability) |
| `list_processors` | `(board_def: dict) -> list` | Return the processors list |
| `resolve_capability` | `(board_def: dict, cap: str) -> dict` | Resolve a capability token to its implementation |

All methods return a response envelope following the existing model-v1 pattern used in instrument interfaces:

```python
{"ok": bool, "outcome": str, "action": str, ...payload}
```

**Proposed location:** `ael/dut/interfaces/base.py` (new, does not exist today)

---

## 12. Capability Resolution Model

Capabilities are declared as a list of string tokens in the board definition:

```yaml
capabilities:
  - build.idf
  - flash.idf_esptool
  - observe.gpio
  - debug.jtag
```

### Resolution Rules

1. The pack loader or pipeline reads the required capability token from the step definition.
2. The DUT registry looks up the board's declared capabilities.
3. If the capability is present, dispatch proceeds to the corresponding adapter.
4. If the capability is absent, the step fails with a clear `capability_not_declared` error rather than silently falling back to a default.

### Capability Token Namespace

| Prefix | Meaning |
|---|---|
| `build.*` | Build system (e.g., `build.idf`, `build.cmake`, `build.pico`, `build.arm_debug`) |
| `flash.*` | Flash method (e.g., `flash.idf_esptool`, `flash.gdb_swd`, `flash.bmda_gdbmi`) |
| `observe.*` | Observation channel type (e.g., `observe.gpio`, `observe.uart`, `observe.la`) |
| `debug.*` | Debug interface (e.g., `debug.swd`, `debug.jtag`) |
| `verify.*` | Verification strategy (e.g., `verify.gpio_signature`, `verify.uart_banner`) |
| `power.*` | Power control capability (e.g., `power.rail_switch`) |

---

## 13. Verification Design Guidance

**Current state:** Verification logic is scattered across several files:
- `ael/default_verification.py` — orchestrates verification runs, worker management
- `ael/pipeline.py` — runs individual pipeline steps including verify stages
- `configs/boards/<id>.yaml` — contains `verification_views` (named scenarios with pin mappings and descriptions)
- `ael/verification_model.py` — defines `VerificationSuite`, `VerificationTask`, `VerificationWorker` dataclasses

`verification_views` in board configs is the closest existing analog to formalized verification profiles. It is a dict of named scenarios, each specifying a pin alias and human description. This needs to be promoted into a first-class `verification_profiles` field.

### Target: Verification Profiles

Each board definition should declare `verification_profiles` as a dict of named scenarios:

```yaml
verification_profiles:
  signal:
    capability: verify.gpio_signature
    pin: sig
    resolved_to: P0.3
    description: GPIO signature capture on PA2 (~250Hz primary signal)
    expected_freq_hz: 250
    tolerance_pct: 10
  led:
    capability: verify.led_blink
    pin: led
    resolved_to: LED
    description: Operator-visible PA8 LED blink (1Hz, active-high)
    expected_freq_hz: 1
```

Rules:
1. Every profile entry must declare a `capability` token.
2. Pin aliases must resolve through `observe_map`.
3. At least one profile named `signal` or `primary` must exist for a board to pass the `verified.status: true` gate.
4. Profile names must be stable across firmware revisions unless the observation point changes.

---

## 14. Doctor / Recovery Design Guidance

The `doctor` command on a DUT should verify that the DUT is in a state where a run can proceed. It differs from instrument `doctor` in that it checks DUT-side concerns, not probe-side concerns.

### DUT Doctor Checklist

| Check | Description |
|---|---|
| `power_rails` | Confirm expected power rails are present (if measurable) |
| `instrument_binding` | Confirm the declared `instrument_instance` is reachable |
| `probe_reachability` | Confirm the control probe can reach the board's debug interface |
| `flash_verify` | Optionally confirm last flashed firmware matches expected hash |
| `gpio_sanity` | Optionally confirm a known GPIO output is toggling (requires powered board) |

### Recovery Guidance

Recovery actions should be layered:

1. **Soft recovery:** Reset DUT via probe, re-run instrument preflight.
2. **Medium recovery:** Power-cycle DUT if power rail control is available.
3. **Hard recovery:** Flag DUT as unavailable and notify operator; do not retry indefinitely.

The recovery strategy should be declared per board class:
- `standard`: soft recovery first, then hard.
- `special`: hard recovery only by default (non-standard reset behavior).
- `composite`: per-processor recovery, escalate to full board reset if any processor fails.

---

## 15. Recommended Directory Structure

The `ael/instruments/` directory already establishes the pattern to follow:

```
ael/instruments/
    interfaces/
        base.py          # InstrumentProvider dataclass
        registry.py      # resolve_manifest_provider(), resolve_control_provider()
        stlink.py        # STLink-specific provider implementation
        esp32jtag.py     # ESP32 JTAG provider implementation
    backends/
        stlink_backend/  # Low-level driver
        esp32_jtag/      # Low-level driver
```

The DUT layer should follow this same structure:

```
ael/dut/                           # NEW — does not exist today
    interfaces/
        base.py                    # DUTProvider dataclass (analog to InstrumentProvider)
        registry.py                # resolve_dut_provider(), load_board_definition()
    backends/
        manifest_adapter.py        # Wraps existing manifest.yaml + board config dicts
    runtime/
        dut_instance.py            # DUTInstance runtime class
    __init__.py
```

### Existing directories to update (not replace):

```
assets_golden/duts/<id>/
    manifest.yaml                  # Currently: identity + build/flash only
    docs.md                        # Board documentation (already exists for some boards)

configs/boards/<id>.yaml           # Currently: wiring, observe, verify views, bench layout
                                   # Target: eventually merged into a unified dut definition
                                   # or formally referenced from manifest.yaml

configs/processors/<mcu_id>.yaml   # NEW — processor profiles (does not exist today)
```

---

## 16. Recommended Data Shape

### Current State (Two Files)

**`assets_golden/duts/esp32c6_devkit/manifest.yaml`** (actual):
```yaml
id: esp32c6_devkit
mcu: esp32c6          # single string — to be replaced
family: esp32
description: ESP32-C6 DevKit GPIO waveform + UART banner (minimal phase-1 path)
build:
  type: idf
  project_dir: firmware
flash:
  method: idf_esptool
tags: [esp32, esp32c6, devkit]
verified:
  status: false
```

**`configs/boards/rp2040_pico.yaml`** (actual):
```yaml
board:
  name: RP2040 Pico
  target: rp2040
  instrument_instance: esp32jtag_rp2040_lab
  build: { project_dir: firmware/targets/rp2040_pico, artifact_stem: pico_blink }
  observe_map: { sig: P0.0, gpio16: P0.0, ... }
  verification_views:
    signal: { pin: sig, resolved_to: P0.0, description: ... }
  bench_connections: [...]
  power_and_boot: { reset_strategy: pulse_reset, boot_mode_default: normal, power_rails: [...] }
```

### Target State (Unified Board Definition)

```yaml
id: esp32c6_devkit
board_class: standard
name: ESP32-C6 DevKit
processors:
  - id: esp32c6
    family: esp32
    architecture: rv32imac
    role: primary
    debug_interface: jtag
description: ESP32-C6 DevKit GPIO waveform + UART banner
capabilities:
  - build.idf
  - flash.idf_esptool
  - observe.gpio
  - observe.uart
  - debug.jtag
build:
  type: idf
  project_dir: firmware
flash:
  method: idf_esptool
instrument_instance: esp32jtag_c6_bench
observe_map:
  sig: P0.0
  gpio8: P0.0
verification_profiles:
  signal:
    capability: verify.gpio_signature
    pin: sig
    resolved_to: P0.0
    description: GPIO signature capture on GPIO8
bench_connections:
  - from: GPIO8
    to: P0.0
  - from: GND
    to: probe GND
default_wiring:
  jtag: P3
  reset: NC
  verify: P0.0
power_and_boot:
  reset_strategy: reset_pin
  boot_mode_default: normal
  power_rails:
    - name: 3V3
      nominal_v: 3.3
tags: [esp32, esp32c6, devkit]
verified:
  status: false
  date: 2026-03-07
  bench_id: pending_hw
```

---

## 17. Future-Proofing Recommendations

1. **Version the board definition schema.** Add a `schema_version: "0.1"` field to all board definitions from the start. This enables controlled migration when breaking changes are needed.

2. **Keep processor profiles DRY.** As more STM32 variants are added, processor profile reuse will prevent duplication of architecture and toolchain fields across manifests.

3. **Design connection profiles for multi-bench labs.** Some boards will be connected differently on different benches. `connection_profiles` with named variants (e.g., `bench_a`, `bench_b`) enables this without forking board definitions.

4. **Align verification profiles with the evidence model.** The `evidence.py` module already captures run evidence. Verification profiles should declare what evidence keys are expected, so completeness checks can be automated.

5. **Avoid embedding test-plan logic in board definitions.** The board definition should declare what can be observed; the test plan should declare what to assert. These must remain separate.

6. **Instrument binding should be overridable at runtime.** The `instrument_instance` in the board definition is a default. Runs should be able to override it via CLI flag or test plan annotation without modifying the board definition.

---

## 18. Non-Goals

This specification does **not** define:

- How test plans are written or validated.
- The instrument model (already defined in `ael/instruments/interfaces/`).
- CI/CD pipeline integration.
- How `assets_user/` overrides are resolved at runtime (that is a resolver policy concern).
- Multi-tenant or networked DUT management (future work).
- Firmware development toolchain configuration beyond what is needed for build/flash dispatch.

---

## 19. Acceptance Criteria

A board definition implementation is complete when:

- [ ] `board_class` field is present and valid.
- [ ] `processors[]` list replaces the single `mcu` string field.
- [ ] `capabilities` list is non-empty and covers at minimum `build.*`, `flash.*`, and one `verify.*` token.
- [ ] `verification_profiles` is present with at least one named entry.
- [ ] `observe_map` covers every pin referenced in `verification_profiles`.
- [ ] `assets.py` `_REQUIRED_FIELDS` has been updated to require `processors[0].id` instead of `mcu`.
- [ ] `find_golden_reference()` queries `processors[].id` and `processors[].family`, not flat `mcu`/`family`.
- [ ] The `ael/dut/interfaces/base.py` `DUTProvider` interface exists and is implemented.
- [ ] At least one existing board definition has been migrated to the unified schema.
- [ ] All existing verified boards pass the new schema validation without regression.

---

## 20. Final Recommendation

**Start with an adapter, not a rewrite.**

The instruments layer succeeded by introducing `InstrumentProvider` as a thin interface that wraps existing behavior. The DUT layer should follow the same pattern:

1. Create `ael/dut/interfaces/base.py` with a `DUTProvider` dataclass.
2. Create `ael/dut/backends/manifest_adapter.py` that wraps the existing manifest + board config dicts.
3. Add `ael/dut/interfaces/registry.py` that resolves a board ID to a `DUTProvider`.
4. Migrate `assets.py` `_REQUIRED_FIELDS` from `mcu` to `processors[]`.
5. Convert one verified board (recommend: `rp2040_pico` — already has `verified.status: true`) to the unified schema.
6. Validate that the `default_verification.py` worker path for `rp2040_pico` still works.

Do not attempt to merge the two files (manifest + board config) in one step. That is a separate operation that should happen after the interface layer is stable.

---

## 21. Revision Notes

This section documents changes made relative to the original chat-draft specification, based on direct inspection of the codebase.

### Changes Made

| Change | Reason |
|---|---|
| Added explicit "Current State" column to Section 6 (Required Fields) | The original draft assumed a unified model already existed. The codebase has two separate files per DUT — manifest.yaml and configs/boards/<id>.yaml — and both must be acknowledged. |
| Noted that `mcu` single-field must migrate to `processors[]` with a specific call-out to `assets.py` `_REQUIRED_FIELDS` | Direct inspection of `ael/assets.py` confirmed `mcu` is listed in `_REQUIRED_FIELDS` as a flat string. This is a concrete migration task, not just a schema preference. |
| Added note in Section 10 that runtime state has no formal home today | `ael/dut/` directory does not exist. Runtime code passes raw dicts through `pipeline.py` and `default_verification.py`. |
| Section 11 (DUT Interface) now includes explicit note that this interface does not exist yet | The codebase uses direct dict access throughout. The `InstrumentProvider` pattern from `ael/instruments/interfaces/base.py` is identified as the model to follow, not an abstract pattern. |
| Section 13 (Verification Design Guidance) revised to reference actual files | `verification_views` in board configs (e.g., `configs/boards/stm32g431cbu6.yaml`, `configs/boards/rp2040_pico.yaml`) is the existing analog. `ael/default_verification.py`, `ael/pipeline.py`, and `ael/verification_model.py` are the relevant source files. |
| Section 15 (Directory Structure) revised to follow `ael/instruments/interfaces/` + `ael/instruments/backends/` pattern | This is the established pattern in the repo, not an invented one. The structure is directly derived from the existing `ael/instruments/` tree. |
| Section 16 (Data Shape) uses actual manifest.yaml and board config content | The original chat draft showed synthetic examples. The revised section uses the actual content of `assets_golden/duts/esp32c6_devkit/manifest.yaml` and `configs/boards/rp2040_pico.yaml`. |
| Section 9 (Multi-Processor) calls out `rp2350_pico2` as the first composite candidate | `rp2350_pico2` is confirmed to exist in `assets_golden/duts/` and does not currently declare `board_class`. |
| Added specific file paths throughout | All references to files use absolute or repo-relative paths that are confirmed to exist in the codebase. |
| Removed abstract "vendor" and "ecosystem" framing | The original chat draft used ecosystem-level language. This spec is scoped to the actual `ai-embedded-lab` codebase and its specific file layout. |
