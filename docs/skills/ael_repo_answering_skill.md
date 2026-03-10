# AEL Repo Answering Skill

## Purpose

`ael_repo_answering` is a lightweight skill specification for answering factual and operational questions about AEL from the right source layer.

It is a workflow skill, not a runtime feature.

Supporting guidance:

- [AEL Agent Answering Guide](../agent_answering_guide.md)

## Trigger / When To Use

Use this skill when the user asks questions such as:

- what is AEL
- what is instrument X
- how is board Y connected
- how do I use AEL
- what does stage X mean
- how do you know this
- what command shows this formally

## Inputs

Typical inputs:

- the user question
- optional board id
- optional test path
- optional instrument id
- optional stage name
- optional historical context if the question is about the past

## Canonical Commands

Instrument identity:

- `python3 -m ael instruments describe --id <id>`

Instrument health:

- `python3 -m ael instruments doctor --id <id>`

Board/test setup:

- `python3 -m ael inventory describe-test --board <board> --test <test>`
- `python3 -m ael inventory describe-connection --board <board> --test <test>`

Stage explanation:

- `python3 -m ael explain-stage --board <board> --test <test> --stage <stage>`

Connection consistency:

- `python3 -m ael connection doctor --board <board> --test <test>`

System overview:

- `docs/what_is_ael.md`
- `docs/specs/ael_architecture_v0_2.md`

## Procedure

1. Identify the question class.
2. Choose the strongest available formal source.
3. Use resolved CLI output first if it exists for that question.
4. Confirm with config/spec files if needed.
5. Use code only for behavior details not exposed elsewhere.
6. Answer directly.
7. State how the answer is known.
8. Mention caveats or provisional assumptions explicitly.
9. If the question is historical, say what source layer provides the historical answer.

## Compact Answer Templates

### What is X?

- `X is ...`
- `I know this from <command/file>.`
- `Current caveat: ...` if needed

### How do you know?

- `Formally, this comes from <command/file>.`
- `That is <resolved/config/runtime/architecture> truth.`

### What command shows this formally?

- `Use: <command>`
- `That shows the resolved current view.`

### How do I use Y?

- `Use Y through <command/doc>.`
- `For current operational details, prefer <command>.`

### What are the caveats?

- `Confirmed facts: ...`
- `Assumptions or provisional items: ...`

## Fallback / Recovery

If no resolved CLI path exists:

1. use current config/spec sources
2. use code for behavior details
3. explicitly say the answer is inferred from current implementation or config

If sources disagree:

- prefer resolved CLI for current resolved state
- prefer current specs/configs for declared structure
- call out the disagreement explicitly

If the question is historical:

- use dated notes, git history, prior run artifacts, or prior docs
- do not answer only from current config

## Outputs

This skill should produce answers that are:

- direct
- source-grounded
- explicit about how they were derived
- explicit about assumptions and caveats

## Summary

`ael_repo_answering` is the answering workflow skill for AEL. Its job is to make sure agents answer from the right source layer and can explain how they know.
