# Experiment Result Capture Skill v0.1

## Purpose
- convert one real bench run into reusable project knowledge
- distinguish clearly between design/readiness and real execution evidence
- prevent experiment knowledge from remaining only in chat history or ad hoc notes

## Scope
- one experiment/demo result at a time
- one board/fixture variant at a time
- one conclusion at a time

This skill is intended for:
- live-pass capture
- repeat-pass capture
- blocked/failure capture
- closeout note generation
- project-memory upgrade decisions

It is not intended for:
- broad analytics dashboards
- generic lab databases
- replacing raw run artifacts

## Inputs
- board
- fixture variant
- exact wiring
- capability/demo name
- firmware/test artifact used
- instrument path(s) used
- run evidence
- repeat count if any
- observed failure mode(s) if any

## Outputs
- structured experiment result record
- concise closeout note
- updated proven-vs-proposed status
- updated anchor confidence if justified

## Evidence Requirements
To upgrade a path from proposal/readiness to execution evidence, require:
- a real bench run
- identifiable run/test artifact(s)
- enough evidence to say what actually passed or failed
- explicit statement of what the result proves and does not prove

Classification upgrade thresholds:
- one successful bounded live run upgrades the path to `live-pass`
- repeated successful bounded live runs upgrade the path to `repeat-pass`
- any anchor-confidence change must be stated explicitly in the result record or closeout

Repeat-pass claims require:
- more than one successful live run
- or one bounded repeat batch with consistent behavior

## Result Classification Rules
Use these classifications:
- `design-confirmed`
- `contract-complete`
- `live-pass`
- `repeat-pass`
- `blocked`
- `failed`

Rules:
- only real bench evidence upgrades a path to `live-pass`
- only repeated successful bench evidence upgrades a path to `repeat-pass`
- if external conditions prevent meaningful execution, classify as `blocked`
- if the experiment ran and did not satisfy its success criteria, classify as `failed`

## Stop Points
Stop and do not overstate the result if:
- run evidence is incomplete
- the result is dominated by unresolved external bench/network instability
- the path did not actually exercise the intended success contract

## Repo Interaction
This skill should write:
- one structured result record
- one short closeout/health note if warranted
- optional status/catalog update only when the evidence clearly justifies it

Raw run artifacts remain in:
- `runs/...`

Durable project-memory upgrades belong in:
- `docs/specs/...`
- machine-readable result records/templates

## Standard Closeout Order
Use this order for closeout notes:
1. fixture/wiring
2. proof method
3. run evidence
4. what this proves
5. what this does not prove
6. anchor impact

For new-board bring-up closeout notes, also include:
7. cleaned full-suite rerun result
8. DUT registration result
9. representative default-verification decision
10. if added, live default-verification evidence

## How It Upgrades Project Memory
This skill is the bridge between:
- raw run evidence
- durable project memory

It should answer:
- what was actually proven
- what remains only proposed
- whether an anchor board/path just got stronger
- whether a path is now ready to be reused later without re-proving the same thing from scratch
