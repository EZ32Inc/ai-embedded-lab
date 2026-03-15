# AEL Copy-First / System Branch Growth Architecture v0.1

## 1. Purpose

### Why copy-miss cannot remain a dead end

When a user requests a board or test that has no known system capability, AEL currently enters an `exploratory` state and asks clarifying questions — then stops. No new capability is created. This is a dead end: the user cannot proceed, and the system does not grow.

A copy-miss should instead trigger capability creation. The system should be able to respond to unmet demand by building new capability, not just reporting absence.

> **Note — v0.1 scope boundary:** The full "copy miss → automatically create new capability" flow is recognized as the intended future behavior, but is **not required to be implemented in v0.1**. In this version, the branch infrastructure and lifecycle model are established first. Capability creation from copy-miss is a next-phase gap, explicitly deferred.

### Why we do NOT want two separate production systems

One alternative is to let users create capability directly in a user domain (`assets_user/`) that operates permanently in parallel with the system domain (`assets_golden/`). This leads to permanent fragmentation: user-side capability is never reviewed, never validated to system standards, and never benefits other users. Two parallel production systems with no convergence path is not the goal.

### Why user-side workflow should remain copy/reuse-first

Users benefit most from well-tested, mature capability. The primary path should always be: find an existing system capability and reuse it. This keeps user interactions fast, reduces errors, and keeps the system as the authoritative source of validated capability.

New capability should be created only when reuse genuinely fails — not as the first resort.

### Why new capability should grow in the system domain, not the user domain

New capability created from user need is still system capability. A new board support entry, a new test plan, or a new firmware target is an addition to AEL's capability set — not a personal user artifact. It belongs in the system domain, subject to system lifecycle and governance.

The difference is that it starts in a **branch** of the system domain, not directly in the main validated layer.

---

## 2. Core Architecture

```
User request
    │
    ▼
Known system capability on main?
    │
    ├─ YES → copy / reuse → run
    │
    └─ NO (copy miss)
           │
           ▼
       Create capability in system branch          ← next-phase gap; not in v0.1
           │
           ▼
       Capability is draft / runnable in branch
           │
           ├─ User can run it immediately from branch
           │
           └─ Branch capability may later be validated
                  │
                  └─ Merge candidate → governance review → promoted to main
```

**Key rules:**

- Users primarily consume/reuse capabilities from system main.
- If reuse fails, the system creates new capability in a **system-domain branch**, not in a user-private space.
- Branch capability is usable and shareable, but is not yet validated to main standards.
- Main contains only mature, validated, officially supported capability.
- Moving a branch capability to main is a deliberate governance action, not automatic.
- New capability does not bypass the branch stage to go directly to main.

**Implementation note — v0.1:**
In this version, "system-domain branch" is implemented as a **logical namespace** (`assets_branch/`), not as a git branch. This is the minimal viable carrier for the branch concept. Git branching may be considered in a later version if the logical model proves insufficient.

---

## 3. Key Definitions

**Capability** — A self-contained, runnable unit of board support in AEL: the combination of a board config, a test plan, and a DUT firmware target that together enable a specific test to run on a specific MCU/board.

**Copy-first** — The default user workflow: find an existing system capability that matches the user's need and reuse it directly, without creating anything new.

**Copy miss** — The condition where no existing system capability matches the user's request closely enough to reuse. In the full architecture, this triggers branch creation. In v0.1, it identifies the gap; automated creation from copy-miss is deferred.

**System main** — The primary, validated layer of AEL capability. Corresponds to `assets_golden/` and associated board configs. Contains capabilities that have been reviewed and confirmed to meet system quality standards.

**System capability branch** — In v0.1, a logical namespace (`assets_branch/`) where new or experimental capability lives before it is ready for main. Not a git branch at this stage. Capability here may be used by projects before promotion to main.

**Promote** — The governance action of moving a validated branch capability into system main (`assets_golden/`). Corresponds to the existing `dut promote` concept. Requires the capability to have reached at least `validated` lifecycle stage.

**Maturity / lifecycle_stage** — A field on a capability artifact indicating how validated it is. Progresses through the capability lifecycle defined below.

**Board config** — A shared hardware description file under `configs/boards/`. Board config is not branched in v0.1; it is written directly to the shared location regardless of whether the associated capability is on branch or main. Branch-specific board config variation is deferred until a real need appears.

---

## 4. Capability Lifecycle

Each capability passes through the following stages, tracked via a `lifecycle_stage` field in its manifest:

| Stage | Meaning |
|---|---|
| `requested` | User need identified; copy miss confirmed; capability creation initiated |
| `draft` | Capability artifacts created (board config, test plan, DUT entry) but not yet runnable end-to-end |
| `runnable` | Capability can execute; at least one successful run recorded |
| `validated` | Capability has passed systematic verification; behavior confirmed stable |
| `merge_candidate` | Capability is proposed for promotion to system main; under review |
| `merged_to_main` | Capability is part of system main; governed under main branch standards |

A capability may remain useful and in use at any stage from `runnable` onward without ever reaching `merged_to_main`. Not all branch capabilities need to promote.

The `lifecycle_stage` field in v0.1 is added to DUT manifests (`manifest.yaml`) and is the primary maturity signal used by inventory reporting and promote gating.

---

## 5. User Workflow

**Normal path (copy hit):**

1. User requests a board/test/capability.
2. System checks known capabilities on system main (`assets_golden/`).
3. Match found → capability is reused or copied to user project context.
4. User runs the capability.

**Branch path (copy miss — full architecture, partially deferred in v0.1):**

1. User requests a board/test/capability.
2. System checks known capabilities on system main. No match.
3. System creates new capability in `assets_branch/`. *(automated creation is next-phase; v0.1 establishes the namespace and lifecycle but does not yet automate step 3)*
4. User's project is linked to the branch capability via `capability_source` and `capability_ref` fields in `project.yaml`.
5. User runs the branch capability immediately (no waiting for promotion).
6. Capability progresses through lifecycle stages as testing accumulates.
7. If the capability reaches `validated`, it becomes a promote candidate.
8. Promotion to main happens via governance review, independently of user workflow.

---

## 6. Visibility

The system should be able to report:

- **Main capabilities**: boards and tests fully supported on system main (`assets_golden/`), with `lifecycle_stage: merged_to_main`.
- **Branch capabilities**: capabilities in `assets_branch/` with their current `lifecycle_stage`.
- **Promote candidates**: capabilities at `validated` or `merge_candidate` not yet in main.
- **Branch capability origin**: which user project triggered the creation of a given branch capability.

---

## 7. Governance

**Core rules:**

- New capability never goes directly to system main. It always starts on a branch.
- System main is the mature/strict layer. Additions require explicit promote action.
- Branch capability is not second-class: it is useful, shareable, and may be used in production user workflows before promotion.
- A capability that is never promoted to main is not a failure.
- The decision to promote is independent of the decision to use.
- Promote requires `lifecycle_stage: validated` (or higher). A capability that has not been validated cannot be promoted.

---

## 8. Deferred Complexity

The following are explicitly out of scope for this version:

- **Automated copy-miss → create new capability flow.** This is the key next-phase gap. Architecture recognizes it; v0.1 does not solve it.
- Git branch implementation. Logical namespace (`assets_branch/`) is sufficient for v0.1.
- Branch naming conventions and automated branch management.
- Branch cleanup, archival, and deletion policies.
- Multi-user branch ownership and conflict resolution.
- Automated promote readiness detection.
- Promotion approval workflows and tooling beyond the `lifecycle_stage` gate.
- Branch-specific board config variation.
- Capability deprecation and removal from main.

---

*Spec version: v0.1 — architecture direction with implementation-aware constraints. Updated after code-aware review.*
