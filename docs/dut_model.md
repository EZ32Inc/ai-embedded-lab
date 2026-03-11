# AEL DUT Model

## 1. Purpose

This document explains how AEL should model a DUT (Device Under Test), what the current repository already supports, and where the model still needs consolidation.

Its goals are:
- define DUT as a first-class concept
- separate DUT identity from board policy and bench setup
- explain current implemented behavior versus target architecture
- guide future refactoring away from ad hoc board-specific handling

## 2. Core Position

The preferred AEL model is:

- a DUT is the thing being tested
- a board profile is policy and execution metadata for a DUT family or board type
- a bench setup is the external environment connected to that DUT

These are related, but they are not the same object.

In practical terms:
- DUT answers "what target is under test"
- board config answers "how AEL builds, flashes, and observes it by default"
- bench setup answers "what external hardware is connected for this test"

## 3. Confirmed Current Repo State

Confirmed:
- AEL already has DUT assets under `assets_golden/duts/` and `assets_user/duts/`
- AEL already has DUT-facing CLI flows such as `dut create` and `dut promote`
- `docs/assets.md` already describes golden vs user DUT assets and promotion
- inventory code already treats DUTs as a meaningful repo-level object

Also confirmed:
- live execution still depends heavily on `configs/boards/<id>.yaml`
- test plans often reference a `board` directly, and some may also reference `dut`
- there is not yet a single clearly enforced DUT runtime abstraction used everywhere in execution code

So the DUT model exists, but execution is still board-profile-centric.

## 4. What a DUT Should Mean in AEL

A DUT should represent the test target as an asset with identity and expectations.

Recommended DUT contents:
- stable DUT id
- MCU/family identity
- purpose or description
- test/pack defaults
- firmware/project references where appropriate
- known-good verification expectations
- documentation for wiring, behavior, and caveats
- verification history or promotion metadata

A DUT should not implicitly absorb:
- the full bench definition
- the full instrument fleet definition
- arbitrary host policy unrelated to the target itself

## 5. Relationship Between DUT, Board Profile, and Test Plan

The intended relationship should be:

### DUT

Represents:
- target identity
- reusable target-level metadata
- default verification intent

### Board profile

Represents:
- build defaults
- flash method defaults
- reset/observe defaults
- target-specific execution policy needed by tooling

### Test plan

Represents:
- a specific verification activity
- runtime checks and expected behavior
- bench setup and required instruments for that activity

This separation matters because the same DUT may:
- be verified by more than one test plan
- run on more than one bench arrangement
- share build policy with a board family while still differing in test intent

## 5.1 Runtime Boundary

In runtime and explanation outputs, AEL should prefer:

- `selected_dut` for target identity
- `selected_board_profile` for board-policy identity
- `selected_bench_resources` for bound external resources

This boundary is important because board profile is not DUT identity.
Board profile explains how AEL will build/flash/observe by default.
DUT explains what target is being verified.

## 6. Current Operational Reality

Today, AEL runtime behavior is driven primarily by:
- board config
- test plan
- optional DUT asset lookup for asset-oriented workflows

This is workable, but it means:
- DUT is not yet the single center of runtime identity
- some behavior that belongs to a DUT or test asset still lives in board policy
- some user-facing concepts can drift apart if docs and configs are not kept aligned

## 7. Recommended Canonical Model

The target model should make DUT explicit without collapsing everything into it.

Recommended structure:

1. DUT asset
- stable target identity
- test/pack defaults
- target documentation
- promotion and verification metadata

2. Board/runtime profile
- build/flash/reset/observe defaults
- toolchain and transport policy

3. Test plan
- specific check logic
- required instruments
- bench setup
- pass/fail semantics

4. Execution record
- run id
- selected DUT
- selected board profile
- selected test plan
- selected instruments
- resulting evidence

## 8. Why This Matters

A clear DUT model improves:
- asset promotion workflow
- reproducibility of verification
- inventory clarity
- board bring-up reuse
- future support for multiple DUT instances of the same board family

Without a clearer DUT model, AEL risks:
- overloading board configs with target-identity concerns
- making golden vs user assets less meaningful in live execution
- creating confusion about what exactly was verified

## 9. Migration Direction

The next steps should be incremental.

### Phase 1: Clarify documentation

- document DUT, board profile, and test plan as separate concerns
- keep existing CLI behavior, but explain it more explicitly

### Phase 2: Improve execution reporting

- surface selected DUT identity more consistently in results and explanation paths
- make it easier to tell whether a run is board-selected, DUT-selected, or both
- prefer a canonical `selected_dut` object in structured outputs, with older flat board fields kept only for compatibility where necessary
- add a peer `selected_board_profile` object so board policy is explicit instead of being hidden inside DUT selection

### Phase 3: Tighten resolver policy

- define clearer precedence between `--dut`, board config, and test-plan hints
- reduce ambiguous cases where the board is the only visible runtime identity

### Phase 4: Consolidate runtime model

- move more target-identity behavior into DUT-aware resolution
- keep board config focused on runtime/tool policy

## 10. Confirmed Constraints and Reasonable Interpretation

### Confirmed

- DUT assets are already real and repo-supported
- board configs remain the dominant runtime input for build/flash/observe defaults
- the repo is not yet using a single unified DUT runtime object everywhere

### Reasonable interpretation

- the main next need is consolidation, not invention
- AEL should become more DUT-aware in runtime reporting and resolution over time

### Open questions

- how strongly should live execution prefer DUT selection over board selection
- whether every active board config should map one-to-one to a DUT asset
- what minimal runtime DUT object should be passed through execution paths

## 11. Related Files

- [docs/assets.md](/nvme1t/work/codex/ai-embedded-lab/docs/assets.md)
- [ael/assets.py](/nvme1t/work/codex/ai-embedded-lab/ael/assets.py)
- [ael/inventory.py](/nvme1t/work/codex/ai-embedded-lab/ael/inventory.py)
- [configs/boards/esp32c6_devkit.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/boards/esp32c6_devkit.yaml)
- [docs/default_verification_execution_model.md](/nvme1t/work/codex/ai-embedded-lab/docs/default_verification_execution_model.md)

## 12. Short Guidance

When designing new AEL features:
- treat DUT identity as distinct from board runtime policy
- keep test intent in test plans
- keep bench/instrument wiring outside the DUT unless it is truly target-intrinsic
- make runtime output say clearly what DUT was actually verified
