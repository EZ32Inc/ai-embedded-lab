# Connection Contract Retrieval

## Purpose

Define the formal retrieval path for answering connection questions about any AEL test.

## Core Rule

When asked "what is the connection for this test?", answer from the formal contract first.

Use sources in this order:

1. `python3 -m ael inventory describe-test --board <board> --test <test>`
2. The test plan under `tests/plans/`
3. The board profile under `configs/boards/`
4. Firmware source only to identify missing contract data

Do not start from firmware source when a resolved `describe-test` path exists.

## Required Answer Structure

Answers should separate:

- Formal contract:
  What `describe-test`, the test plan, and the board profile explicitly declare.
- Inferred implementation detail:
  What firmware source suggests but the formal contract does not declare.
- Missing contract data:
  What should be formalized if the answer still depends on code inspection.

## Expected Commands

Primary resolved view:

```bash
python3 -m ael inventory describe-test --board <board> --test <test> --format text
```

Optional connection-only view:

```bash
python3 -m ael inventory describe-connection --board <board> --test <test> --format text
```

## Interpretation Rules

- If `describe-test` already shows the needed wiring or bench setup, answer from that output.
- If the test plan adds `bench_setup` facts such as `serial_console`, `peripheral_signals`, or `external_inputs`, treat those as part of the formal contract.
- If a needed signal exists only in firmware source, say that the formal contract is incomplete and identify the missing field explicitly.

## Verification Rule For New Examples

New generated examples should be considered connection-contract-ready only if:

1. `inventory describe-test` resolves successfully
2. the operator can answer the connection question from formal contract surfaces alone for the normal bench path
3. any missing external stimulus or bus contract is stated explicitly in plan metadata

## Related Files

- [AI_USAGE_RULES.md](/nvme1t/work/codex/ai-embedded-lab/docs/AI_USAGE_RULES.md)
- [ael_connection_spec_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/ael_connection_spec_v0_1.md)
- [example_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/example_generation_policy_v0_1.md)
