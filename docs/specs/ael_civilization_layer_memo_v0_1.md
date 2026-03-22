# AEL Civilization Layer — Memo v0.1

**Status:** Draft
**Date:** 2026-03-21
**Source:** Extracted from AEL design discussion with ChatGPT
**Companion spec:** `AEL_Civilization_Engine_V0_1_Spec.md` (in docs/)

---

## I. Background

Through a series of discussions about AEL — starting from specific engineering problems (DUT/Board/Instrument modeling, ESP32-S3/C6 dual-USB-path handling, auto test generation under minimal-wiring constraints) — a more significant pattern has emerged:

**AEL is a system that gets stronger the more it is used.**

This is not about accumulating more data or logs. It means:

- Each real engineering task or experiment can expose a planner gap, abstraction gap, or skill gap
- Once that gap is analyzed and corrected, the fix can be recorded
- The recording is then distilled into a reusable skill
- Future similar tasks can automatically invoke that skill
- Therefore, the system's first-pass quality continuously improves

This property — capability growth through experience accumulation — is what this memo calls the **Civilization Layer** (文明层), and its primary implementation module is called the **AEL Civilization Engine** (also referred to as Experience Engine in implementation contexts).

---

## II. Core Conclusions

### 1. AEL Is a System That Gets Stronger Through Use

This must be elevated to a core system property, not a side observation.

"Gets stronger through use" does not mean:
- More data accumulates
- Logs get longer
- Configuration grows richer

It means:
- Each real task can expose a planning/cognitive gap
- The gap gets analyzed and fixed
- The fix process and correct approach are recorded
- That recording gets distilled into a reusable skill
- Future similar problems invoke that skill automatically
- Therefore the system does better the first time

Capability growth happens both at the development level (engineers using AEL) and at the usage level (end users running tasks).

### 2. AEL's Development Resembles Civilizational Progress, Not Individual Intelligence Growth

The appropriate analogy:

Human civilization today is far more capable than 10,000 years ago — not because individual human brains fundamentally changed, but because:
- Experience can be preserved
- Knowledge can be transmitted
- Failures and successes can be recorded
- Later generations don't start from zero
- Progress builds on accumulated foundations

AEL without an experience accumulation mechanism is like a highly intelligent individual who starts fresh each time — capable in the moment but not retaining useful patterns. With experience accumulation, it begins to exhibit **civilizational** characteristics:

- Oral tradition stage → discussions produce good conclusions, but they disperse if not written down
- Written record stage → recording cases, failure-to-success paths
- Manual / standard stage → distilling experience into rules, skills, best practices
- Education stage → new tasks retrieve past experience, inject into planning
- Scientific method stage → propose hypothesis → experiment → record failure → revise rule → verify transfer → distill skill

### 3. The Distinction Between "Stronger" and "More Conservative"

The goal is **maturity**, not conservatism.

| More conservative | More mature |
|-------------------|-------------|
| Tends to reuse old templates | Uses existing experience to raise the starting point |
| Slows down on new situations | Still makes dynamic judgments for current context |
| Only repeats old approaches | Knows when to follow experience and when to deviate |
| Unnatural when deviating | Can explain why it's deviating |

Civilization assets should **enhance** AI, not **constrain** it. The civilization layer is a lever, not a cage.

---

## III. The Four Asset Layers

To prevent AEL's cognitive assets from mixing together, they must be explicitly separated into four layers:

### Layer 1: Knowledge
Static facts, definitions, object relationships.

Examples:
- Board is not the DUT
- Instrument can be located on the board
- GPIO / PWM / ADC / I2C are peripheral capabilities

### Layer 2: Rules
Executable judgment criteria.

Examples:
- Test generation starts from DUT capability
- Dual access paths share one firmware model
- Zero-wire tests ranked before minor-wiring tests
- `location: onboard` instruments have wiring cost = 0

### Layer 3: Experience
Complete records of a specific task or experiment.

Contents:
- Initial plan (what AEL first tried)
- Where it went wrong
- How it was corrected
- Whether correction succeeded
- Whether it transferred to a new scenario

### Layer 4: Skills
Reusable method templates distilled from experience.

Examples:
- How to handle board-level modeling
- How to generate a minimal-wiring test plan
- How to recognize multiple onboard instruments as shared-path execution bindings

If these four layers are not kept separate, cognitive assets become a confused pile. Once separated, each layer has clear management, update, and deprecation logic.

---

## IV. Two Types of Experience — Both Must Be Recorded

### Type 1: Failure-Correction Experience

What it contains:
- Common error patterns
- Why the error happened
- What the correct abstraction is
- How to move from a wrong plan to a right plan
- How to prevent the same error in the future

These are distilled into **correction skills**. They are most valuable for helping AEL avoid repeating mistakes.

### Type 2: First-Time Success Experience

What it contains:
- Correct first reaction
- Correct planning order
- Correct object modeling approach
- Correct output structure

These are distilled into **best-practice / planning skills**. They help AEL perform like a professional engineer the first time on similar problems.

**Both types are required.** Recording only successes misses the prevention of future mistakes. Recording only failures misses the reuse of validated best approaches.

---

## V. Planning Quality Is the Highest Priority

A key insight from recent experiments:

> **Verify planning quality first. Verify execution quality second.**

For AEL, a wrong planner may accidentally produce some correct output. A right planner will consistently generalize to new scenarios. Long-term system quality depends on the reliability of the planner.

**The standard experiment flow must therefore be:**
1. Ask for the plan first
2. Evaluate the plan against known principles
3. If the plan is wrong → fix the planner before running
4. Then evaluate execution output

---

## VI. Capability Growth Unit

Traditional project metrics count:
- How many boards supported
- How many features implemented
- How many tests written

For AEL, the more meaningful unit of growth is the **capability unit**:

- Ability to correctly model Board / DUT / Instrument relationships
- Ability to do minimal-wiring test planning
- Ability to convert experience into skills
- Ability to recognize multi-access-path shared firmware
- Ability to generate test families from DUT capabilities

A capability unit, once formed, reuses across many future problems — far more valuable than a single feature.

**AEL's capability growth is compounding, not additive:**
- A new skill can improve many similar problems
- A new rule can change a whole class of planner behavior
- A new correct abstraction can influence future system object modeling

---

## VII. Skill Promotion Lifecycle

Not all experience should immediately become a global default rule:

```
Raw Case
  ↓ (extract)
Candidate Skill
  ↓ (verified in at least one transfer scenario)
Verified Skill
  ↓ (validated across multiple similar problems)
Core Skill    ← becomes default planning policy
```

**Skill expiration:** Not all experience stays valid forever. Some skills are stage-specific, board-specific, or superseded by better skills. The civilization layer is not only-additive — it should support skill promotion, demotion, and deprecation.

---

## VIII. Public vs. Project Civilization Assets

As AEL grows in scope, civilization assets will naturally split:

### Public Civilization Assets
Broadly applicable general engineering experience:
- Board is not the DUT
- Planner quality first
- Minimal-wiring reasoning priority
- Dual path → look for shared model first

### Project Civilization Assets
Specific to a project, board family, or architecture:
- Specific board schema conventions for a given project
- Specific download path handling for a given platform
- Local wiring optimizations for a specific test family

Keeping these two categories separate prevents the civilization layer from becoming unmanageable as it grows.

---

## IX. The Ideal State: Old Experience as Starting Point, New Discoveries Feed Back

The full compounding loop:

```
Civilization Engine enhances AI
  → AI exceeds old experience in new tasks
    → New experience is absorbed back into Civilization Engine
      → Civilization Engine continues to advance
```

If this loop runs correctly, the Civilization Engine is not just an accumulation layer — it is a living civilization system.

---

## X. AEL Civilization Engine — Module Definition

### Official Name
**AEL Civilization Engine**
(In implementation contexts also called: AEL Experience Engine / 经验引擎)

### One-Line Definition

> AEL Civilization Engine is the core system block that captures, organizes, reuses, and compounds engineering experience into reusable civilization assets, enabling AEL to grow stronger through use.

### Chinese Definition

> AEL 文明引擎是 AEL 中用于记录、组织、复用并持续放大工程经验的核心系统模块，它将经验转化为可复用的文明资产，使 AEL 在使用中持续变强。

### What It Carries

- Real experiment experience (cases)
- Failure correction paths
- First-time success paths
- Reusable skills
- Executable rules
- Planner guidance
- Correction patterns
- Capability growth records

### What It Does

- Helps AEL enter the correct planning path faster in new tasks
- Reduces repeated mistakes
- Improves first-pass professional quality
- Converts one experience into future capabilities

---

## XI. Minimum Implementation Requirements (V0.1)

The first version should be minimal and focused on proving the loop works:

### Must Have
1. **Raw case recording** — save the full story of an important task (scene, first plan, error, correction, final approach, skill IDs extracted)
2. **Skill files** — one file per skill, containing: `skill_id`, `title`, `kind` (planning/correction/execution), `applies_to`, `trigger patterns`, `core rule`, `use_when`
3. **Anti-pattern files** — one file per known bad pattern: `pattern_id`, `description`, `why_wrong`, `correct_approach`
4. **Simple retrieval** — keyword or tag based matching, no complex vector search needed in V0.1
5. **Planning injection** — before AEL starts planning a new task, retrieve relevant skills and inject them into the planning context

### Must NOT Have (in V0.1)
- Complex UI
- Database (file-based storage is correct for V0.1)
- Auto-summarization or auto-extraction (human-curated for V0.1)
- Fancy vector search
- Anything that delays getting the loop working

### Acceptance Criteria
- [ ] A skill file written → retrieved when similar task arrives
- [ ] A correction anti-pattern recorded → AEL avoids that error on similar next task
- [ ] Planning injection is part of the standard flow
- [ ] The loop is: record → retrieve → inject → improved first-pass quality

---

## XII. Key Sentences for the Record

> AEL is a system that gets stronger the more it is used.

> AEL's capability growth should come not only from code changes, but from capturing, structuring, and reusing experience as skills.

> Both failure-correction experience and first-time-success experience should be recorded and turned into reusable skills.

> The goal is that when a similar problem appears again, AEL can get it right the first time and respond like a professional engineer.

> This may be a small implementation step, but it is likely a major system step. It adds very little code, yet it may fundamentally change AEL from a system that can be improved into a system that can accumulate and reuse experience.

> The Civilization Engine is a lever, not a cage. It should enhance AI, not constrain it.

---

## XIII. Relationship to Other AEL Components

| Component | Relationship |
|-----------|-------------|
| AEL planner | Primary consumer of civilization assets — skills are injected before planning |
| AEL experiments | Primary producer of civilization assets — each experiment feeds new cases and skills |
| AEL doctor | Secondary consumer — civilization assets can inform doctor guidance and explanations |
| AEL test generation | Benefits from planning skills for board/DUT/test reasoning |
| AEL compatibility engine | Benefits from rules about compatibility judgment patterns |

---

*Extracted from AEL design discussion. Companion docs: `ael_experiment_methodology_v0_1.md`, `AEL_Civilization_Engine_V0_1_Spec.md`*
