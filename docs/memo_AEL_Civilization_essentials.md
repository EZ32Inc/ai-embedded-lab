# Memo — AEL Civilization
## Essential Version

## 1. Core judgment
AEL is not just an automation system. It is becoming a system that **gets stronger through use**.

Each real task can produce more than an answer or a test result. It can produce:
- a corrected abstraction,
- a planning rule,
- a reusable skill,
- an anti-pattern,
- or a better engineering method.

## 2. What the Civilization idea means
The key breakthrough is to treat these high-value outcomes as **civilization assets** rather than temporary discussion results.

That means:
- experience should be recorded,
- successful methods should be reusable,
- failure-to-success paths should also be reusable,
- and future tasks should start from prior accumulated experience rather than from zero.

This is why the term **Civilization** fits: the system grows by preserving and reusing engineering experience.

## 3. Why this is different from traditional software
Traditional software usually becomes stronger mainly through code changes.

AEL can become stronger through:
- rules,
- skills,
- planner corrections,
- experience capture,
- and repeated reuse.

This makes growth cheaper, faster, and more natural.

## 4. The most important principle
**AI-driven remains the core.**

Civilization assets must help AI do better work. They must **not** become rigid templates that suppress AI judgment, creativity, or adaptation.

So the relationship is:
- AI provides reasoning, planning, and generation.
- Civilization assets provide memory, guidance, correction patterns, and leverage.

The engine should make AEL more mature, not more rigid.

## 5. What should be recorded
AEL should record both:

### A. Failure-to-success experience
This captures:
- what was misunderstood,
- why it was wrong,
- how it was corrected,
- and how to avoid repeating the same mistake.

### B. First-time-success experience
This captures:
- what a good first plan looks like,
- what the correct abstraction is,
- and what a strong engineering approach looks like from the start.

Both are essential.

## 6. Why planning matters more than execution first
For AEL, many of the most valuable improvements happen in **planning**, not execution.

If planning is wrong, the whole path is often wrong.

So civilization assets should first improve:
- object modeling,
- task decomposition,
- planning sequence,
- minimal-cost strategy,
- and test generation direction.

## 7. Current embedded engineering example
The recent Board / DUT / Instrument discussions revealed several high-value civilization assets already:
- Board is not DUT.
- A board can contain DUTs and instruments.
- Multiple onboard instruments may be alternate access paths to one DUT.
- Test generation should start from DUT capabilities, not instrument type.
- Minimal wiring should be treated as a first-class planning objective.

These are exactly the kinds of things that should become reusable civilization assets.

## 8. Why the first version should stay small
The first goal is not to build a large or general system.

The first goal is to prove a **small closed loop**:
1. capture one real case,
2. extract a few skills and anti-patterns,
3. retrieve them for a similar new task,
4. inject them before planning,
5. show that the next first plan is better.

If this loop works, the civilization seed is real.

## 9. Embedded-first, facade-later
The first implementation should be **embedded-first**.

There is no need to over-design for every future engineering field right now.

If the core mechanism works well in embedded engineering, future domain expansion can be added through lighter facade or domain layers, while keeping the core civilization mechanism stable.

So the correct strategy is:
- build a strong embedded core first,
- let the civilization seed grow,
- expand later only when needed.

## 10. Why this can grow like a real civilization
A real civilization does not begin large. It begins in a few small places with a few strong seeds.

AEL can grow the same way.

At first:
- few users,
- few cases,
- few skills,
- narrow scope.

But if experience can be captured, reused, and compounded, then use itself becomes growth fuel.

That means the system can grow from a few local engineering strengths into a much broader and more powerful civilization of reusable engineering knowledge and practice.

## 11. The role of anti-patterns
Civilization assets should not contain only best practices.

They should also contain **anti-patterns**, such as:
- do not treat board as DUT,
- do not generate tests from instrument type first,
- do not skip planner correction when the plan is obviously wrong,
- do not let stored skills become rigid constraints.

Knowing what not to do is part of engineering maturity.

## 12. What AEL Civilization Engine is
The practical system block for this is the **AEL Civilization Engine**.

Its purpose is to:
- capture engineering experience,
- organize it,
- store skills and anti-patterns,
- retrieve them for similar future tasks,
- and inject them before planning.

Its purpose is not just storage. Its purpose is **future improvement**.

## 13. Final takeaway
AEL Civilization is the idea that engineering experience should not disappear after each task.

Instead, it should become reusable system capability.

If this works, AEL will not just complete tasks. It will continuously improve how it plans, reasons, and acts — and it will do so in a way that looks increasingly like a mature professional engineering system.
