# User Project Layer Validation Closeout v0.1

Reference spec: `docs/specs/User Project Layer Validation Spec v0.1.txt`

## Summary

Both validation scenarios have been completed. The user project layer is
considered proven for v0.1 for the two representative cases defined in the spec.

---

## Scenario A: STM32F411 — Mature Path

### What happened

1. User requested: "Create a project for STM32F411 with LED blinking and GPIO toggling."
2. System identified `stm32f411ceu6` as a known mature path (high confidence).
3. Project shell created: `projects/stm32f411_first_example/`
4. System ran `stm32f411_gpio_signature` test end-to-end:
   - Build: Cortex-M4 gcc, clean
   - Flash: SWD via `esp32jtag_stm32f411`, 3.3V confirmed
   - Verify: PA2 GPIO toggle captured (758 edges / 252ms), PC13 LED blinking confirmed
   - Result: **PASS** (`run_id: 2026-03-14_21-29-20_stm32f411ceu6_stm32f411_gpio_signature`)
5. Project status updated to `validated`. Run evidence linked.

### Acceptance criteria — met

| Criterion | Status |
|---|---|
| A1: Project created/updated, goal recorded, status coherent | ✓ |
| A2: Execution connected — build/flash/verify ran end-to-end | ✓ |
| A3: Transparency — mature path reuse declared | ✓ (`mature_path_reused: True`) |
| A4: Result tied to real run evidence, not generated text | ✓ (run_id, PASS, confirmed_facts) |

### Gaps found and fixed during Scenario A

- `inventory describe-test --test <name>` failed with bare test names → fixed: now resolves to `tests/plans/<name>.json`
- Project state after a successful run was not auto-updated → fixed: `project link-run` command added
- `project status` lacked transparency fields → fixed: `path_maturity`, `mature_path_reused`, `run_evidence` added
- No formal A/B/C/D output on project create for known boards → fixed: Batch H

---

## Scenario B: STM32F407 — Unknown / Not-Yet-Mature Path

### What happened

1. User request simulated: "Create a project for STM32F407."
2. System ran `_resolve_maturity("stm32f407")` → `path_maturity: inferred` (matched to `stm32f401rct6` family, medium confidence).
3. Project shell created with `status: exploratory`.
4. Output included structured WARNING + clarification question list.
5. `project run-gate` blocked with reason: "path_maturity is inferred — not a verified match."
6. `project questions` returned the unknown-path question set (board type, LED pin, GPIO, debug tool).

For a fully unknown MCU (e.g. `nrf52840`):
- `path_maturity: unknown`, `status: exploratory`
- run-gate blocked with reason: "no mature path found"
- clarification questions returned

### Acceptance criteria — met

| Criterion | Status |
|---|---|
| B1: No fake maturity — system did not inherit F411/F401 config as confirmed | ✓ |
| B2: Controlled clarification — minimum required questions asked | ✓ |
| B3: Project created in `exploratory` mode, not `validated` | ✓ |
| B4: Correct reuse boundary — family-level reference labeled as inferred only | ✓ |

### Gaps found and fixed during Scenario B

- No maturity detection existed → fixed: `_resolve_maturity()` function added
- `project create` had no path_maturity field → fixed: field added to project.yaml
- No run gate existed → fixed: `project run-gate` command added
- `project questions` returned generic questions regardless of maturity → fixed: branches on `path_maturity`

---

## Clarify-First Gap Found After Both Scenarios

### Problem identified

Even for Scenario A (mature path), the system was inheriting repo instrument/wiring/setup
as if they were the user's confirmed real setup. This was not acceptable per
the validation spec's transparency requirement (A3).

### Additional work done

- New policy: `docs/specs/known_board_clarify_first_policy_v0_1.md`
- Skill updated: `docs/skills/user_project_creation_skill.md` — added Rule 2 (clarify-first for known boards)
- Agent guide updated: `docs/agent_answering_guide.md` — added known-board setup confirmation section
- CLI: `project create` now outputs A/B/C/D structured block for mature paths (H1)
- CLI: `project questions` for mature paths now shows 4 confirmation-checklist items (H2)
- CLI: `project run-gate` for mature paths checks real-setup confirmation state (H3)
- 2 AI behavior test cases added for known-board clarify-first

---

## Rules Derived From This Work

1. **Known repo path ≠ confirmed user setup.** A candidate path match requires explicit user confirmation of board variant, instrument, wiring, and intended test before being treated as runnable.

2. **Unknown path must not pretend maturity.** If `_resolve_maturity()` returns `inferred` or `unknown`, the system must use `status: exploratory`, show clarification questions, and block `run-gate`.

3. **Project state must reflect real execution.** After a validated run, `project link-run` must be used to record `run_evidence`, update `confirmed_facts`, and set `status: validated`.

4. **Transparency is required.** `project status` must show `path_maturity`, `maturity_confidence`, `mature_path_reused`, and `run_evidence` so the user and agents can always tell what is real vs assumed.

5. **Post-plan missing-info output is mandatory.** After identifying a candidate path, the system must proactively show what is still missing — the user must not have to guess.

---

## Implementation Summary

| Component | File | Change |
|---|---|---|
| Maturity detection | `ael/__main__.py` | `_resolve_maturity()` |
| Project create maturity | `ael/__main__.py` | `_project_create_shell()` with `path_maturity`, `repo_root` |
| A/B/C/D output | `ael/__main__.py` | `_load_candidate_path_info()`, H1 block |
| Confirmation check | `ael/__main__.py` | `_mature_confirmation_check()` |
| Questions branching | `ael/__main__.py` | H2 mature/unknown branch |
| Run gate | `ael/__main__.py` | `project run-gate` command, H3 mature check |
| Run linkage | `ael/__main__.py` | `project link-run` command |
| Transparency fields | `ael/__main__.py` | `project status` output |
| Policy spec | `docs/specs/known_board_clarify_first_policy_v0_1.md` | New |
| Skill update | `docs/skills/user_project_creation_skill.md` | Rule 2 added |
| Agent guide | `docs/agent_answering_guide.md` | Known-board section added |
| AI behavior tests | `tests/ai_behavior_cases/organic_cases.yaml` | 9 new test cases total |

---

## Remaining Open Items (intentionally deferred)

- **Runtime CLI enforcement of confirmation checklist**: The policy is doc/skill-level. No code gate prevents `ael run` from executing without project confirmation. A future `ael run --project <id>` integration could check `run-gate` first.
- **Auto-populate confirmed_facts from user conversation**: Currently, `confirmed_facts` is only updated by `project link-run` (from real run results) or `project update --append-confirmed-fact`. A structured intake command for user-provided confirmations would complete the loop.
- **Wiring confirmed fact**: No command currently writes "Wiring confirmed: ..." to confirmed_facts. This needs an explicit user-confirmation write-back path.
- **Multi-user project management**: Deferred per `docs/specs/ael_user_concept_v0_1.md`.

---

## Conclusion

The first practical version of the user/project workflow is proven.

Both scenarios — known mature path (STM32F411) and unknown/inferred path (STM32F407) —
behave correctly, with appropriate transparency, clarification, and execution linkage.

The clarify-first gap was identified and closed with policy + CLI changes.

The system is ready for real-world use within the scope of v0.1.
