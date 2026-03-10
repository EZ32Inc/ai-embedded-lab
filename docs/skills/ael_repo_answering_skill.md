# AEL Repo Answering Skill

## Purpose

`ael_repo_answering` is a lightweight skill specification for answering factual and operational questions about AEL formally, consistently, and from the right source layer.

It is intended for AI agents working in the AEL repo, including Codex and Gemini-style CLI agents.

## Why This Skill Matters

AEL now has several source layers:

- architecture and spec documents
- board and instrument configs
- resolved CLI views
- implementation code

Without a formal answering workflow, agents can answer from the wrong layer and produce:

- stale answers
- implementation-heavy answers when a formal resolved view exists
- guessed bench facts stated as confirmed truth

This skill exists to prevent that.

## Trigger / When To Use

Use this skill when the user asks questions such as:

- what is AEL
- what is instrument X
- how is board Y connected
- how do I use AEL
- what does stage X mean
- how do you know this
- what command shows this formally

Use it for both:

- narrow operational questions
- broader repo-understanding questions

## Inputs

Typical inputs:

- the user question
- optional board id
- optional test path
- optional instrument id
- optional stage name

The question may be direct or vague.

## Source Selection Rule

Always choose the most formal current source available.

Priority order:

1. resolved CLI output
2. current manifests, configs, and specs
3. implementation code
4. older narrative docs only as support

Supporting guidance:

- [AEL Agent Answering Guide](/nvme1t/work/codex/ai-embedded-lab/docs/agent_answering_guide.md)

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

System architecture:

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

## Expected Answer Shape

Preferred shape:

1. direct answer
2. how it is known
3. command or file source
4. caveat if needed

Do not force all four every time if the user wants a very short answer, but the answer should still be traceable.

## Question-Type Guidance

### What is AEL?

Use:

- `docs/specs/ael_architecture_v0_2.md`

Support with current CLI examples only if the user asks how it is used in practice.

### What is instrument X?

Use:

- `python3 -m ael instruments describe --id <id>`

Support with:

- instrument manifest
- backend code only if protocol details are requested

### How do you use AEL?

Use:

- current CLI and workflow docs
- architecture/spec docs only for conceptual framing

### What is the connection for board/test Y?

Use:

- `python3 -m ael inventory describe-connection --board <board> --test <test>`

### What does stage X do?

Use:

- `python3 -m ael explain-stage --board <board> --test <test> --stage <stage>`

## Common Pitfalls

- quoting raw config without checking the resolved CLI view
- treating provisional board assumptions as confirmed hardware truth
- answering operational questions from architecture docs alone
- using code as the first source when a formal resolved command exists

## Recovery / Fallback

If no resolved CLI path exists:

1. use current config/spec sources
2. use code as the behavior source
3. explicitly say the answer is inferred from current implementation/config rather than resolved runtime output

If sources disagree:

- prefer resolved CLI output for current runtime-facing truth
- prefer current spec/config for declared structure
- call out the disagreement explicitly

## Outputs

This skill should produce answers that are:

- direct
- source-grounded
- explicit about how the answer was derived
- explicit about assumptions and caveats

## Summary

`ael_repo_answering` is the formal answering workflow skill for AEL. Its main job is to make sure agents answer from the right source layer and can say how they know what they are saying.
