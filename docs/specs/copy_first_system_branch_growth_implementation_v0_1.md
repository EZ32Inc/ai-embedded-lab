# AEL Copy-First / System Branch Growth — Minimal Implementation Target v0.1

## 1. Purpose

This document defines the smallest coherent implementation needed to validate the architecture described in `copy_first_system_branch_growth_v0_1.md`.

This is not the full end-state. It establishes the branch infrastructure, lifecycle tracking, and project linkage so that the architecture can be exercised and validated in practice. The key next-phase capability (automated copy-miss → create new capability) is explicitly deferred.

---

## 2. Current Baseline

The following already exists and should be reused without modification:

| Existing feature | Location | Role in new architecture |
|---|---|---|
| Golden/user inventory scanning | `ael/inventory.py` — `("golden", assets_golden/duts)` + `("user", assets_user/duts)` | Extend to also scan `assets_branch/duts` |
| `dut create` (copy from golden) | `ael/__main__.py` `dut_create_cmd()` | Reuse as the branch capability seed operation |
| `dut promote` (user → golden) | `ael/__main__.py` `dut_promote_cmd()` | Reuse as "promote to main"; add maturity gate |
| `project.yaml` linkage fields | `closest_mature_ael_path`, `cross_domain_links`, `mature_path_reused` | Extend with two new fields; do not break existing fields |
| `verified.status` in manifest | All DUT `manifest.yaml` files | Retain; `lifecycle_stage` is added alongside it |
| Board config location | `configs/boards/*.yaml` | Unchanged; board config is not branched in v0.1 |
| Pipeline execution | `ael/pipeline.py` `run_pipeline()` | Unchanged; branch capabilities use the same pipeline |

---

## 3. v0.1 Implementation Target

### 3.1 Logical branch namespace

Create `assets_branch/duts/` as the physical carrier for branch-stage capabilities.

- Structure mirrors `assets_golden/duts/` exactly.
- A capability placed here is "on branch" by definition.
- No git branch is created. The directory is the namespace.
- Add `.gitkeep` to establish the directory in the repo.

### 3.2 Branch visibility in inventory

Extend `inventory.py` `build_inventory()` to include a third scan source:

```python
("branch", root / "assets_branch" / "duts")
```

Each branch DUT entry in inventory output should include:
- `source: "branch"`
- `lifecycle_stage` (read from manifest, see 3.3)

`ael inventory` or `ael board state` output should distinguish branch capabilities from main capabilities.

### 3.3 `lifecycle_stage` field in manifest

Add `lifecycle_stage` as an optional field to DUT `manifest.yaml`. Valid values:

```
draft | runnable | validated | merge_candidate | merged_to_main
```

Rules:
- `dut create` writes `lifecycle_stage: draft` when creating a branch DUT.
- `lifecycle_stage` is separate from `verified.status`; both may coexist.
- A DUT in `assets_golden/` with no `lifecycle_stage` field is implicitly `merged_to_main`.

### 3.4 Promote gating on maturity

Update `dut_promote_cmd()` to enforce: `lifecycle_stage` must be `validated` (or `merge_candidate`) before promotion is allowed.

If a DUT has no `lifecycle_stage`, treat `verified.status: true` as sufficient for backward compatibility.

`dut_promote_cmd()` should also update `lifecycle_stage` to `merged_to_main` in the destination manifest after promotion.

### 3.5 Minimal project linkage to branch capability

Add two new fields to `project.yaml`:

```yaml
capability_source: "branch"   # "main" | "branch" (default: "main")
capability_ref: "<dut_id>"    # the DUT id in assets_branch/ this project is using
```

Rules:
- These fields are optional. Projects referencing main capabilities do not need them.
- `closest_mature_ael_path` is retained as-is; it continues to point to the nearest known main path for reference.
- `cross_domain_links` may add a new entry with `type: branch_capability_ref` when a project links to a branch DUT.

### 3.6 Terminology alignment

Ensure the following mappings are consistently applied in code output and CLI messages:

| Spec term | Code/CLI term |
|---|---|
| system main | `assets_golden/` |
| system branch | `assets_branch/` |
| promote | `dut promote` |
| lifecycle_stage | `lifecycle_stage` field in manifest |
| copy miss | path_maturity = unknown / no inventory match |

---

## 4. Explicit Non-Goals for v0.1

Do not implement any of the following in this version:

- **Automated copy-miss → create new capability.** This is the primary deferred gap. The branch namespace exists, but automatic capability generation from a copy-miss is not part of v0.1.
- Git branch implementation. `assets_branch/` directory is sufficient.
- Advanced branch governance or approval workflows.
- Branch cleanup, archival, or deletion tooling.
- Multi-user branch conflict handling.
- Branch-specific board config (`configs/boards_branch/` or equivalent). Board config stays in `configs/boards/` for all capabilities.
- Automated promote readiness detection or CI hooks.
- Visibility UI beyond what `ael board state` and `ael inventory` already provide.

---

## 5. Recommended Implementation Order

Implement in this sequence to avoid partial states:

1. **`assets_branch/duts/` directory** — create the namespace (trivial, establishes physical carrier)
2. **`lifecycle_stage` in manifest** — add field definition, update `dut_create_cmd()` to write `draft`
3. **Inventory scan extension** — add `("branch", assets_branch/duts)` to `build_inventory()`; expose `lifecycle_stage` in output
4. **Promote gate** — update `dut_promote_cmd()` to check `lifecycle_stage >= validated`; write `merged_to_main` on success
5. **project.yaml linkage** — add `capability_source` + `capability_ref` fields to project create / update flows; update `_project_create_shell()` to write them when a branch capability is referenced

Each step is independently testable before the next begins.

---

## 6. Acceptance Criteria

This v0.1 implementation is complete when:

- [ ] `assets_branch/duts/` exists in the repo and is scanned by inventory.
- [ ] A DUT created with `dut create` in `assets_branch/` carries `lifecycle_stage: draft` in its manifest.
- [ ] `ael inventory` (or equivalent) shows branch DUTs separately from golden DUTs, with `lifecycle_stage` visible.
- [ ] `dut promote` on a DUT with `lifecycle_stage: draft` or `runnable` is rejected with a clear message.
- [ ] `dut promote` on a DUT with `lifecycle_stage: validated` succeeds and writes `lifecycle_stage: merged_to_main` to the destination manifest.
- [ ] A `project.yaml` can carry `capability_source: "branch"` and `capability_ref: "<id>"` without breaking existing project commands.

---

## 7. Future Work

Items recognized by this architecture but deferred beyond v0.1:

| Item | Why deferred |
|---|---|
| Automated copy-miss → create new capability | Requires capability generation logic; too broad for v0.1 |
| Git branch model for system branches | Logical namespace is sufficient to validate the architecture first |
| Branch naming conventions | Not needed until multiple branches exist |
| Branch cleanup / archival policy | Not needed until branches accumulate |
| Multi-user branch conflict handling | Single-user scenario is sufficient for v0.1 |
| Board config branching (`configs/boards_branch/`) | No real need identified yet; revisit if it appears |
| Automated promote approval / review workflow | Manual `dut promote` with `lifecycle_stage` gate is sufficient |
| Deeper governance tooling | Deferred until the basic lifecycle is validated in practice |

---

*Implementation target version: v0.1 — minimal validation scope only.*
