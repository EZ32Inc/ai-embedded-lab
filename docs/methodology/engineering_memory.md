# AEL Methodology: Engineering Memory and Growing Assurance

## 1. Introduction

Traditional software and embedded development systems mainly preserve two kinds of information:

- source code
- technical documentation

These preserve the **final result**, but rarely preserve **how the result was produced**.

In real engineering work, some of the most valuable knowledge exists in the development process itself, such as:

- symptoms
- diagnostic reasoning
- failed attempts
- fixes
- verification methods

This information usually does not enter the repository in a structured way, so it is often lost after the task is completed.

AEL introduces a different principle:

> **Do not only save the result. Save the process.**

By automatically preserving engineering process, the system can accumulate experience over time and form a continuously strengthening engineering assurance system.

---

## 2. The limitation of traditional SDKs

Traditional MCU SDKs, such as those from ST, usually provide:

- drivers
- example code
- API documentation

But they usually do **not** provide a crucial extra layer:

- how the code was created
- what problems appeared during development
- how the debugging was performed
- why the final implementation was chosen
- what failed before it worked

So users are given:

- example code
- reference documentation

But not:

- the engineering creation path
- the debug path
- the validation path
- the reasoning behind design choices

This means much of the most valuable engineering knowledge remains only in the engineer’s head.

---

## 3. A new paradigm in AEL

AEL adds a new layer on top of the traditional structure:

```text
Code
+ Verification
+ Engineering Process
+ Extracted Experience

So the system evolves from:

code + docs

to:

code
verification
case studies
skills
workflow rules

The key addition is:

Engineering Process Record

This is the beginning of Engineering Memory.

4. Case Documents: preserving engineering trajectory

Each important engineering task should produce a case document.

For example:

STM32F401 bring-up

A case document should preserve:

goal

initial state

reference implementation

execution steps

encountered problems

diagnosis

fixes

verification

extracted skills

follow-up recommendations

A case document therefore captures not just the outcome, but the engineering trajectory.

This is much richer than final code alone.

5. Case First, Skill Second

In AEL, knowledge should be used with this priority:

Case
↓
Skill
↓
Spec
Case

A real engineering case with full context.

Skill

A reusable rule or heuristic extracted from one or more cases.

Spec

A higher-level workflow rule or system policy.

This leads to an important principle:

Case First, Skill Second.

For similar future tasks, a real case often provides more practical value than an abstract rule alone.

6. Why experience documents may be more important than code

In an AI-driven engineering system, experience documents may in many cases be more valuable than code.

6.1 Code is the result

Code mostly preserves final state.

6.2 Experience preserves the path

Experience records:

problem
→ reasoning
→ fix
→ verification
6.3 AI can regenerate code from experience

If the process document includes:

goals

peripheral relationships

configuration logic

validation method

problem/fix history

Then AI can often regenerate or reconstruct the code.

But the reverse is much harder:

code → full engineering process

Therefore, experience documentation often contains higher-value information than the code alone.

7. “Making mistakes becomes harder than doing it right”

As the system accumulates cases and skills, a powerful effect appears:

Making mistakes becomes harder than doing it right.

This happens because the system gradually accumulates both:

known correct paths

known incorrect paths

When AI faces a similar task, it can:

retrieve related cases

compare current context

reuse validated paths

avoid previously known mistakes

This creates a strong engineering property:

correct paths become clearer

wrong paths become harder to follow

repeated mistakes become less likely

This is one of the clearest signs of a healthy engineering memory system.

8. Growing Assurance

Traditional engineering assurance comes from:

coding standards

reviews

tests

CI

regression suites

These are important, but mostly static.

AEL introduces something different:

Growing Assurance

The loop is:

Do work
↓
Record process
↓
Extract experience
↓
Preserve experience
↓
Use experience to guide future work

So every completed task strengthens the system.

Traditional assurance is often static.

AEL assurance grows over time.

That is why the word assurance is so important here.

It is not only about preventing errors in the current task.
It is about making future work increasingly reliable.

9. Engineering Memory

From this perspective, AEL is not just an AI coding system.

It is becoming an Engineering Memory System.

Engineering Memory includes:

case studies

debugging paths

validation records

extracted skills

workflow rules

verified examples

known-good and known-bad paths

This allows the system to act less like a model writing code from scratch, and more like an experienced engineer drawing on prior work.

10. Why this matters in the AI era

In the pre-AI era, code was often the most scarce and valuable output.

In the AI era, code generation becomes easier.

What becomes scarce is:

engineering judgment

hardware bring-up knowledge

diagnosis strategy

validation knowledge

real-world lessons from failure

So the core asset shifts from:

code

to:

engineering experience

That is why preserving process is so important.

11. Case documents can guide users too

These documents are not only useful internally for AI.

They can also help users.

When a user says:

“I need a new test”

“I want to create a GPIO experiment”

“How do I build a similar PWM verification?”

“Show me how a similar test was created”

AI can retrieve a similar case and respond with:

a real example of how such a test was created

the reasoning behind the implementation

the debugging path

the verification flow

guidance for creating a similar experiment

This is much more useful than abstract instructions alone.

So case documents become not only engineering records, but also teaching assets.

12. Traditional SDKs lack process documentation

A major difference between AEL and traditional SDKs is this:

Traditional SDKs provide:

code

examples

docs

But not:

creation process

debug process

validation process

extracted engineering experience

So traditional SDKs mainly preserve results.

AEL can preserve results plus process.

That is a genuine paradigm shift.

13. Process should be captured by rule, not by accident

A very important conclusion is this:

Process recording should be a rule.

The system should know before starting a task that the process must be preserved.

That means:

before work: recording is expected

during work: key steps and issues are captured

after work: the case document is generated naturally

This avoids the classic problem:

task completed

process forgotten

only partial summary remains

Instead, process capture becomes part of the workflow itself.

14. Suggested workflow rule

AEL should define something like:

Engineering Task Recording Rule

When performing any significant engineering task, such as:

board bring-up

new test creation

verification suite creation

instrument integration

major refactor

bug investigation with real hardware

The agent must maintain a task record including:

goal

initial state

major execution steps

problems encountered

diagnosis reasoning

fixes applied

verification results

extracted skills

follow-up recommendations

At task completion, the system should generate:

docs/case_studies/<task_name>.md

This turns every important task into a new engineering memory asset.

15. Three layers of knowledge

AEL knowledge should be structured into three levels:

Level 1: Case Studies

Real engineering cases with full context.

Best for:

retrieval

analogy

guidance

understanding full trajectory

Level 2: Skills

Reusable heuristics or rules extracted from cases.

Best for:

repeated application

modular reuse

standardization

Level 3: Specs / Workflow Rules

Higher-level system rules and completion policies.

Best for:

consistency

governance

promotion criteria

workflow enforcement

This creates a clear structure:

case → skill → spec
16. Case documents are first-class assets

Case documents should be treated as formal repository assets, not optional notes.

That means a mature repository should preserve not only:

firmware

tests

configs

but also:

case studies

skills

verification records

workflow methodology

A possible repository structure could become:

repo/
  firmware/
  tests/
  configs/
  docs/
    case_studies/
    skills/
    methodology/
    boards/

This is a very different model from a traditional SDK repository.

17. Case documents can become tutorials

A single case document can generate multiple outputs:

17.1 Engineering Record

A full internal record for developers and AI.

17.2 Tutorial Version

A simplified version for users to learn from.

17.3 Skill Extraction

A reusable rule or heuristic for the system.

This means one real engineering task can create several layers of reusable knowledge.

18. The system becomes self-strengthening

With this structure, the system does not just complete tasks.

It improves itself through task execution.

The loop becomes:

Engineering task
↓
Case capture
↓
Skill extraction
↓
Future guidance
↓
Better future task execution

This is why this new capability feels so important.

It is not just another feature.

It changes how engineering knowledge exists, grows, and is reused.

19. Key principles that emerged

From this discussion, several important AEL principles emerge:

19.1 Do not only save the result. Save the process.
19.2 Experience documentation is a core asset.
19.3 Case First, Skill Second.
19.4 Every significant engineering task should produce an engineering record.
19.5 AEL is naturally growing into an engineering memory system.
19.6 Traditional SDKs preserve code and docs, but usually not process.
19.7 The system can form a growing assurance mechanism.
19.8 Over time, doing it wrong becomes harder than doing it right.
20. The role of assurance

A particularly important concept here is assurance.

This word captures something deeper than testing or validation alone.

AEL does not only verify whether something works once.

It builds a system where:

prior lessons remain available

known failures are remembered

validated paths can be reused

future work starts with more protection than before

So assurance is not only a snapshot.

It becomes cumulative.

This is why it is accurate to say:

The system gains a growing assurance capability.

And that explains the feeling:

Doing it wrong becomes harder than doing it right.

21. A concise summary

The core methodology can be summarized as:

We do not only save results. We save process.
We do not only save process. We extract experience from it.
We do not only extract experience. We preserve it and use it to guide future work.
In this way, the system develops a continuously strengthening engineering assurance capability.

22. Final conclusion

AEL’s deeper value is not only that AI can write code, flash hardware, run tests, and verify results.

Its deeper value is that during all of this, it can also accumulate engineering memory.

This changes the system from:

AI coding tool

into:

AI engineering system

And eventually into:

AI engineering memory system

That is why this new capability is so important.

It is not just about completing work.

It is about ensuring that every completed task leaves behind guidance, protection, and accumulated experience for the next one.

So the key principle is:

Do not only save the result. Save the process.
Then extract experience from the process, preserve it, and use it to guide future work.

That is how AEL gains Engineering Memory and Growing Assurance.
