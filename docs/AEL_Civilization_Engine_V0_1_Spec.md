# AEL Civilization Engine
## V0.1 Design Memo and Implementation Spec

## 1. Why this exists
AEL already shows an unusual property: it gets stronger through use. Real experiments do not only validate behavior; they reveal planning gaps, abstraction mistakes, correction paths, and reusable engineering patterns.

The missing piece is a small but crucial core block that turns those discoveries into future capability. That block is the **AEL Civilization Engine**.

V0.1 should not try to be broad or fancy. It should establish the civilization seed: experience can be captured, turned into reusable assets, and used again before the next similar task is planned.

## 2. Product definition
The **AEL Civilization Engine** is the core system block that captures, organizes, reuses, and compounds engineering experience so that AEL grows stronger through use.

It is not a passive note store. It is an active engine that improves future planning quality by injecting relevant prior experience, skills, anti-patterns, and correction paths into new tasks.

It is also not meant to replace AI reasoning. **AI-driven planning remains the center.** The engine exists to enhance AI with reusable engineering memory, not to constrain it.

## 3. Design principles
- **Embedded-first.** Build a strong embedded engineering core first; do not over-generalize the first implementation.
- **Small seed before large system.** The first goal is a working closed loop, not scale.
- **AI-driven remains core.** Civilization assets are guidance and leverage, not rigid control.
- **Planning first.** The engine should improve planning quality before execution quality.
- **Record both failure-to-success and first-time-success experience.**
- **Promote short, high-leverage skills over long, passive documentation.**
- **Prefer lightweight file-based assets for V0.1.**
- **Design for future facade-based expansion, but do not optimize the first version around distant domains.**

## 4. V0.1 scope
V0.1 is intentionally narrow. It should support real engineering case capture, skill extraction, skill retrieval, and planning-time use in embedded engineering tasks.

It should **not** attempt domain-general reasoning, autonomous skill merging, semantic vector search, or complex ranking logic yet.

It should be easy to implement, easy to inspect, easy to edit, and easy to trust.

### Core V0.1 outcome
Given a new task, AEL should be able to:
1. Retrieve relevant prior civilization assets.
2. Inject them before planning.
3. Produce a materially better first plan than before.

## 5. Functional architecture
V0.1 can be expressed as five cooperating functions:

1. **Case capture**
   - Save a raw case after a real task or experiment.
2. **Skill / anti-pattern extraction**
   - Turn a case into reusable civilization assets.
3. **Registry and storage**
   - Load and organize saved assets.
4. **Retrieval**
   - Match a new task against stored assets.
5. **Planning injection**
   - Provide retrieved assets to AEL before planning.

## 6. Data model
Two file types are sufficient for V0.1: **raw cases** and **skills**.

### Suggested repository structure
```text
 ael_civilization_engine/
   cases/
   skills/
   anti_patterns/
   indexes/
   templates/
```

### Raw case file
Suggested contents:
- `case_id`
- `title`
- `tags`
- `problem`
- `context`
- `first_attempt`
- `issues`
- `fix`
- `final_solution`
- `skills_extracted`

### Skill / anti-pattern file
Suggested contents:
- `skill_id`
- `title`
- `kind` (`planning`, `correction`, `execution`, `anti_pattern`)
- `applies_to`
- `trigger_patterns`
- `rule`
- `use_when`
- `expected_effect`
- optional `confidence`

## 7. Minimal workflow
1. A real task or experiment is completed.
2. A raw case is written, capturing the initial request, first plan, mistakes or gaps, correction path, and final good result.
3. One or more skills are extracted from the case. These may be planning skills, correction skills, execution skills, or anti-patterns.
4. A new but similar task arrives.
5. The engine matches that task against tags and trigger patterns.
6. Retrieved civilization assets are injected before planning.
7. AEL plans with AI-driven reasoning plus relevant prior experience.
8. The new outcome becomes another case, and the cycle continues.

## 8. Primary V0.1 use cases
- Board / DUT / instrument modeling corrections.
- Minimal-wiring test planning for embedded boards.
- Reuse of prior test-generation patterns for GPIO, PWM, ADC, I2C, and similar peripheral families.
- Correction reuse when AEL originally planned in the wrong direction.
- Reapplication of first-time-success patterns to similar future boards.

## 9. Acceptance criteria
V0.1 is successful if it can do all of the following:
- Save at least one real raw case.
- Save at least a few skills and anti-patterns derived from that case.
- Retrieve relevant assets for a similar new task.
- Inject those assets before planning.
- Produce a noticeably better first plan on the follow-up task.
- Do all of this with a simple, inspectable, file-based implementation.

## 10. Explicitly out of scope for V0.1
- Large-scale multi-user civilization aggregation.
- Automatic high-confidence skill promotion and demotion.
- Cross-domain abstraction beyond embedded engineering.
- Vector databases or heavy semantic search infrastructure.
- Complex trust scoring or automated conflict resolution between skills.
- Replacing AI planning with rigid rule execution.

## 11. Implementation plan
1. Define file schemas for cases, skills, and anti-patterns.
2. Implement a tiny loader and registry.
3. Implement keyword/tag/trigger retrieval.
4. Add planning-time injection support.
5. Use one real embedded case to create the first civilization assets.
6. Re-test a similar problem and verify first-pass improvement.
7. Iterate only after the closed loop is proven.

## 12. Recommended first assets
- **Skill:** Distinguish board from DUT.
- **Skill:** Treat multiple onboard instruments as alternate access paths for one DUT.
- **Skill:** Generate tests from DUT capabilities before considering execution binding.
- **Skill:** Prefer zero-wire and low-wire tests before more expensive test plans.
- **Anti-pattern:** Do not treat prior skills as rigid templates that suppress AI judgment.

## 13. Final note
AEL Civilization Engine V0.1 should be judged by **system effect**, not by code size.

If it can reliably make the next similar task materially better, then the civilization seed is real.

That seed is the small implementation step that can become a major long-term system step.
