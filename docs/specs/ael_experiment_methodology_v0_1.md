# AEL Experiment Methodology v0.1

**Status:** Draft
**Date:** 2026-03-21
**Source:** Extracted from AEL design discussion with ChatGPT

---

## 1. Overview

AEL experiments are not just verification runs. They are the primary mechanism by which AEL grows new capabilities.

The difference between AEL experiments and traditional software tests:

| Traditional Tests | AEL Experiments |
|-------------------|----------------|
| Verify existing functionality | Discover capability gaps |
| Pass/fail on known behavior | Evaluate reasoning quality |
| Output: test results | Output: rules, skills, planner improvements |
| System stays the same | System capability increases |

**Core insight:** Each real experiment exposes a planner gap, abstraction gap, or skill gap. Once analyzed and corrected, the fix should be recorded, promoted to a reusable skill, and automatically applied to future similar problems.

---

## 2. The Fundamental Experiment Principle

> **Verify planning quality first. Verify execution quality second.**

A system with a wrong planner may occasionally produce correct output by accident. A system with the right planner will consistently produce correct output across new scenarios.

Therefore:

1. Before asking AEL to generate or execute anything — **ask for its plan first**.
2. Review the plan against known principles.
3. If the plan is wrong, **fix the planner before running**.
4. Only then evaluate the output.

---

## 3. Standard Five-Phase Experiment Loop

### Phase 1 — Ask for the Plan

Before any generation or execution, ask AEL to explain its approach:

- How does it understand the board / DUT / available instruments?
- How does it plan to use the instruments?
- How does it determine "minimum wiring"?
- How does it derive test families from DUT capabilities?
- How does it decide which tests are zero-wire vs. need extra wiring?
- How does it handle two instruments that share the same DUT firmware?

**Goal:** Reveal whether the methodology is correct *before* looking at output.

If the plan shows any of these errors, stop and go to Phase 2:
- Treats board as DUT
- Treats two instruments as two independent test systems
- Only generates console/flash tests (ignores GPIO/PWM/ADC/I2C families)
- Does not start from DUT capabilities
- Does not apply minimal-wiring reasoning
- Does not output wiring cost / explanation

---

### Phase 2 — Record Issues

Do not just say "it's wrong." Solidify each error as a structured issue:

**Issue format:**

```
Issue: <short title>

Observed:
  <what AEL actually did or said>

Expected:
  <what correct behavior looks like>

Fix direction:
  <what rule, principle, or skill needs to be added>
```

**Example:**

```
Issue: Planner treats board as DUT

Observed:
  AEL used the board ID when applying test applicability checks,
  treating the whole board as the test target.

Expected:
  AEL should identify the DUT component (esp32s3_main) within the board,
  and apply test applicability to the DUT, not the board.

Fix direction:
  Add principle: Board is not the DUT. Test applicability checks against
  the DUT, not the board container.
```

---

### Phase 3 — Write the Correct Rules

After identifying issues, write the correct behavior as **explicit principles**.

Do not leave corrections implicit. Write them down so they can be:
- Checked against in future experiments
- Promoted into AEL's skill/rule system
- Used as acceptance criteria for the next run

**Core principles established so far:**

```
P1. Board is not the DUT.
    Board is the physical assembly hosting DUTs and instruments.

P2. Multiple onboard instruments targeting the same DUT
    are two access paths, not two independent test systems.

P3. Test generation starts from DUT capabilities, not instrument types.

P4. Instrument path is execution binding only —
    it does not define the test family.

P5. Prioritize zero-extra-wiring tests first.

P6. Same DUT → same firmware template family,
    regardless of which instrument path is used.

P7. Output must include wiring explanation per test.

P8. Blocked tests must be explicitly reported with reasons.
```

---

### Phase 4 — Re-Run and Evaluate

After fixing the planner and writing correct rules:

1. Re-run the same scenario
2. Compare output against the issue list
3. Check each principle is satisfied
4. Confirm the specific issues from Phase 2 are resolved

Do not accept "it mostly looks better" — check each issue was concretely fixed.

---

### Phase 5 — Repeat Until Correct

Repeat the loop until all Phase 2 issues are resolved and all Phase 3 principles are satisfied in the output.

**Loop template:**
```
Round N:
  1. Observe plan / output
  2. Compare against principles
  3. Record remaining issues
  4. Fix planner / rules / skills
  5. Re-run → go back to step 1
```

---

## 4. Two-Round Validation Protocol

A single successful run is not sufficient to confirm capability growth.

### Round 1 — Learning Round

**Goal:** Fix the planner, establish correct rules, get the first correct output.

This round is "teaching." AEL doing it correctly in Round 1 only proves it was taught for this specific example.

### Round 2 — Transfer Validation Round

**Goal:** Validate that the rules and skills generalize.

Use a **similar but different** board:
- Same structural pattern (board + DUT + onboard instruments)
- Different specific chip or different peripheral exposure
- Slightly different instrument configuration

**Round 2 passes if AEL:**
- Applies all Phase 3 principles **without being re-taught**
- Correctly separates Board / DUT / Instrument for the new board
- Generates tests from DUT capabilities (not instrument types)
- Applies minimal-wiring reasoning correctly
- Does **not** blindly copy Round 1 output (it generalizes, not memorizes)

**Round 2 evaluation criteria:**

| Criterion | Pass condition |
|-----------|---------------|
| Board ≠ DUT | Identified correctly for new board |
| Instrument recognition | Correctly identified as access paths, not test systems |
| DUT capability-first | Starts from new DUT's capabilities |
| Minimal-wiring ranking | Applied correctly without prompting |
| Firmware sharing principle | Applied without re-explanation |
| First-pass quality | No major principles violated in first attempt |

---

## 5. What to Record Per Experiment

For each significant experiment, record:

```markdown
## Experiment Record: <title>

### 1. Background
Why this board/scenario was chosen. What it represents.

### 2. Initial Question
What we asked AEL to do.

### 3. AEL's First Plan (Round 1)
Verbatim or close paraphrase. What did it say?

### 4. Issues Found
List of structured issues (see Phase 2 format).

### 5. Correct Rules Established
The principles written in Phase 3.

### 6. Re-test Result
Did the corrected planner satisfy all issues?

### 7. Transfer Validation (Round 2)
New board used. What changed. Did AEL apply rules automatically?

### 8. Skills Extracted
Which skills were promoted from this experiment?
What is their ID, scope, and trigger?

### 9. Capability Upgrade Summary
What can AEL now do that it could not do before?
```

---

## 6. Classifying What Gets Recorded

Experiment records should produce assets in **four distinct categories**:

### Principles
High-level, stable definitions. Examples:
- Board is not the DUT
- Test generation starts from DUT capability
- Planner quality first, execution quality second

### Rules
Specific executable judgment rules. Examples:
- Zero-wire tests are ranked before minor-wiring tests
- Dual access paths share one firmware model
- `location: onboard` instruments have wiring cost = 0

### Skills
Reusable method templates. Examples:
- `minimal_wiring_test_generation` — how to generate tests under wiring constraint
- `dual_path_execution_planning` — how to handle two instruments for one DUT
- `board_dut_separation_check` — how to correctly identify DUT within a board

### Experiment Records
Full process records (see section 5).

---

## 7. Experience-to-Skill Conversion Process

For each experiment, run this 7-step process to extract reusable skills:

```
Step 1: Record the original task
  What was asked, what was the context.

Step 2: Record the first plan
  What AEL initially said / planned.

Step 3: Record the problem
  Where the first plan was wrong.

Step 4: Record the correction
  What the correct approach is, and why.

Step 5: Extract the skill
  Formalize as: planning skill / correction skill / execution skill.

Step 6: Label the scope
  What types of problems / boards / object models does this skill apply to?

Step 7: Verify reuse
  In the next similar task, does AEL apply this skill automatically?
```

---

## 8. Skill Promotion Lifecycle

Not all experience should immediately become a global default rule. Suggested lifecycle:

```
Raw Case
  ↓ (extract from case)
Candidate Skill
  ↓ (verified in at least one transfer case)
Verified Skill
  ↓ (validated broadly across multiple similar problems)
Core Skill
  (becomes default planning policy)
```

This prevents local, case-specific experience from being prematurely promoted to universal rules.

---

## 9. Principles for Experiments

> **E1.** An experiment is not just a run. It is a capability growth opportunity.

> **E2.** Planning quality must be verified before execution quality.

> **E3.** Issues must be recorded as structured items, not left as vague impressions.

> **E4.** Correct rules must be written explicitly, not left implicit.

> **E5.** Round 1 proves teaching. Round 2 proves learning.

> **E6.** Skills extracted from experiments should be reusable across similar scenarios, not just this specific board.

> **E7.** Record both failure-correction experience AND first-time success experience.

---

*Extracted from AEL design discussion. Companion docs: `ael_auto_test_generation_experiment_spec_v0_1.md`, `ael_civilization_layer_memo_v0_1.md`*
