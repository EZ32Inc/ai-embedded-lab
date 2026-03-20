# Schema Program Summary And Next Test Direction 2026-03-20

## Why This Note Exists

This note summarizes the completed test-plan schema program work, explains why it was a major repo-wide change, evaluates the current stability risk, and recommends the next phase of work.

It is intended as a discussion document, not as a code-level implementation note.

## Executive Summary

The schema work is effectively complete at the current design boundary.

This was not a small metadata addition. It became a repo-wide information-model upgrade that now spans:

- test plan files
- static schema validation
- inventory and explain surfaces
- repo audit and migration tooling
- default verification state and review
- `ael status`
- nightly summary
- review pack and nightly report
- AI/review retrieval guidance

The right next step is not more schema plumbing.

The right next step is practical live validation, centered on `default verification`, to confirm that the new review and readiness signals remain stable under real bench execution.

## What Was Completed

### 1. Test Plan Schema Foundation

A lightweight static schema layer was added and stabilized.

Key outcomes:

- formalized `schema_version`
- formalized `test_kind`
- formalized `supported_instruments`
- formalized `requires`
- formalized `labels`
- formalized `covers`
- preserved legacy-plan compatibility
- introduced structured validation for `schema_version: "1.0"`

This turned plan metadata from an informal convention into a checked contract.

### 2. Plan Migration Across Real Test Families

A large set of real plans was migrated to structured metadata.

This included:

- mailbox families
- minimal-runtime mailbox plans
- meter-backed instrument-specific plans
- banner-style instrument-specific plans
- instrument-owned selftest paths

This was important because it proved the schema on real plan families instead of keeping it theoretical.

### 3. Inventory And Explain Integration

The schema is now consumed by repo-native operator and developer surfaces.

Integrated surfaces include:

- `inventory list`
- `inventory describe-test`
- `stage_explain`
- pre-flight explanation paths

These surfaces now expose:

- plan schema kind
- test kind
- supported instruments
- requires
- labels
- covers
- validation errors
- legacy vs structured distinction
- board-owned vs instrument-owned distinction

That means the schema is no longer just present in JSON files; it is operationally visible.

### 4. Audit And Migration Governance

The repo now has schema audit and migration governance surfaces.

Key outcomes:

- repo-native `audit-test-schema`
- readiness-style audit output
- family summary and test-kind summary
- structured vs legacy visibility
- policy tests for structured plan quality
- sweep coverage for declared schema-version plans

This reduced the risk of partial migration chaos and made the adoption state inspectable.

### 5. Default Verification Integration

This became one of the largest and most important parts of the work.

`default verification` now produces structured review signals, including:

- `schema_review_status`
- `schema_advisory_summary`
- `schema_warning_messages`
- `baseline_readiness_status`

Repo-native command surfaces now include:

- `python3 -m ael verify-default state`
- `python3 -m ael verify-default review`
- `python3 -m ael status`

The project now has a real baseline review path instead of only raw run results.

### 6. Cross-Surface Consistency Work

The same review conclusions are now intentionally aligned across multiple surfaces.

This includes consistency across:

- verify-default state
- verify-default review
- `ael status`
- review-pack payloads
- nightly-report payloads
- nightly summary payloads

This was essential because a schema/review program becomes dangerous if each command tells a slightly different story.

### 7. Nightly / Report / Review Workflow Integration

The schema and readiness information was pushed into higher-level reporting and review workflow surfaces.

Integrated components include:

- review pack payload and markdown
- nightly report payload and markdown
- nightly summary payload
- warning-only readiness advisory in report decision sections

Current reporting surfaces now carry:

- `schema_review_status`
- `structured_coverage`
- `warning_summary`
- `baseline_readiness_status`
- warning-only merge advisory text

### 8. Warning-Only Readiness Signal

A repo-native top-level summary signal now exists:

- `baseline_readiness_status`

Current intended meaning:

- `ready`
- `needs_attention`
- `unavailable`

Important boundary:

This is currently advisory-only.
It does not yet hard-gate execution, runner dispatch, or merge decisions.
That boundary is deliberate and important for stability.

### 9. Closeout And Skill / Retrieval Capture

The work did not stop at code and tests.

It also produced:

- closeout notes
- reusable skill capture
- AI/review retrieval guidance updates
- explicit use of `baseline_readiness_status` in review guidance

This matters because the size of the change means the repo needed memory, not just code.

## Why This Was A Major Change

This program was one of the largest recent project-wide changes because it touched every layer from data definition to operator summary.

It changed:

- how plans declare meaning
- how the repo validates plan meaning
- how operators inspect test meaning
- how baseline review is summarized
- how readiness is surfaced in CLI and reports
- how nightly and review workflows talk about system health
- how AI/review references retrieve baseline-health facts

This is best understood as an information-model upgrade across the project, not as a narrow feature.

## Did This Introduce Stability Risk?

Yes, it introduced real risk.

Any change of this size can create instability through:

- contract drift between surfaces
- accidental execution coupling
- incorrect metadata on migrated plans
- report and review surfaces becoming inconsistent
- false confidence from new status signals

However, the current evidence suggests that the risk is controlled rather than currently destabilizing.

## Why The Repo Does Not Currently Look Unstable

### 1. The Work Was Kept Mostly Advisory

The most important stabilization choice was to keep the new signals advisory-only.

The new schema and readiness signals currently:

- explain
- summarize
- audit
- warn

They do not currently:

- change runner dispatch logic
- hard-block default verification execution
- force merge or release decisions

That sharply reduces the blast radius of mistakes.

### 2. Contract Tests Were Added Repeatedly

This work was not just implemented once and left alone.

Repeated contract tests were added for:

- schema validation
- inventory and explain surfaces
- verify-default state and review
- status output
- report payloads and markdown
- nightly summary
- cross-surface consistency

This is one of the main reasons the system still looks coherent after such a large change.

### 3. Real Live Validation Was Included

The work also included real representative execution, not just unit tests.

Representative paths were run across:

- mailbox-style paths
- meter-backed paths
- banner-style paths

This also surfaced at least one real runtime bug unrelated to schema semantics itself, which was then fixed. That is a useful sign: the work was touching real execution paths rather than hiding entirely in mocked tests.

## Current Judgment

The current judgment should be:

- this was a large and meaningful architectural enhancement
- it did introduce real system-level risk
- but it does not currently appear to have destabilized the repo in a broad uncontrolled way
- the main remaining uncertainty is bench-level and runtime-level stability under repeated real runs, not schema definition correctness

## Is The Schema Work Finished?

At the current intended boundary: yes, basically.

The schema program is complete enough because it already covers:

- schema definition
- migration on real plan families
- operator surfaces
- audit surfaces
- default verification review
- status summary
- nightly and report surfaces
- readiness summary
- warning-only merge advisory
- documentation and skill capture

Additional schema work would now have diminishing returns unless the project explicitly decides to do one of these:

1. introduce a new test kind that the current schema cannot express
2. turn advisory signals into formal gating signals
3. redesign merge/release policy around readiness

Without one of those decisions, more schema work is likely to be plumbing rather than progress.

## Recommended Next Direction

The next direction should be practical validation, not more schema feature work.

The right question is no longer:

- is the schema expressive enough?

The right question is now:

- do the new review and readiness signals remain accurate and stable under real default-verification execution?

## Recommended Testing Strategy

### Phase A: Representative Live Single Runs

Before running a full default baseline repeatedly, run a small set of representative real paths.

Recommended shape:

- 1 mailbox / baremetal path
- 1 meter / instrument-specific path
- 1 banner-style instrument-specific path

Purpose:

- confirm the schema/review/readiness surfaces continue to match real bench behavior
- confirm no path family was made silently brittle by the new metadata/review work

### Phase B: Full Default Verification Single Run

After the representative paths look healthy, run the current default verification baseline once.

Purpose:

- confirm the whole current baseline still runs cleanly
- validate that `verify-default review`, `ael status`, and report surfaces tell the same practical story
- confirm `baseline_readiness_status` aligns with real operator judgment

### Phase C: Limited Repeat / Stability Check

After one clean baseline run, run limited repeat verification.

Recommended options:

- repeat one critical representative path
- or repeat the full baseline a small number of times

Purpose:

- check for flakiness
- see whether readiness signals become noisy under real repetition
- confirm that warnings and health signals are stable enough to trust operationally

## Suggested Practical Batch Plan

A reasonable next testing batch would be:

### Batch A

Run 3 representative live `single_run` validations:

- mailbox representative
- meter representative
- banner representative

### Batch B

Run the current full default verification baseline once.

### Batch C

Run limited repeat verification on one high-value path or the current baseline.

## What Should Not Happen Next

Unless there is a very specific need, the next phase should not:

- keep adding schema fields
- convert advisory signals into hard gates immediately
- make runner dispatch depend on schema semantics
- expand merge/release enforcement before more live validation

That would increase coupling before the new surfaces have had enough real operational exercise.

## Final Recommendation

Stop schema feature work here.

Treat the schema program as complete at the current advisory boundary.
Move into practical testing, centered on `default verification`, with emphasis on:

- representative live paths
- baseline health validation
- repeat stability
- checking whether `baseline_readiness_status` matches real operator judgment

That is the highest-value next step.
