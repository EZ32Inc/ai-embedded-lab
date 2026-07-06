# AEL Unified Task Front Door Memo

Date: 2026-07-06

## Background

The CoreWeaver/RP2040 flashing issue exposed a larger AEL workflow problem.
The concrete bug was not only a flash script detail. The deeper issue was that
an AI operator received a familiar hardware task and initially reconstructed
the procedure from local reasoning instead of entering through AEL's existing
validated experience.

For RP2040 on ESP32JTAG/CoreWeaver, the correct sequence already existed in the
Golden Suite. Once we looked up the Golden Reference and copied the validated
board flash config, the issue became straightforward:

- reuse the RP2040 S3JTAG Golden Reference
- bind it to the current CoreWeaver channel and GDB port
- keep the flash sequence fixed
- prevent generic fallback strategies from changing that known-good sequence
- record the successful live variant back into AEL

This should be treated as a design lesson for all AEL work, not as a one-off
RP2040 lesson.

## Principle

AEL should not depend on the AI agent remembering past debugging sessions.
Known pitfalls, known good sequences, board resources, test coverage, and
validated runs should be represented as reusable code and data.

The desired model is:

```text
human intent -> AEL task front door -> task classification -> reference lookup
             -> structured plan -> execution -> evidence -> experience update
```

The undesired model is:

```text
human intent -> AI improvises commands -> repeated debugging of solved problems
```

## Scope Beyond Flashing

The RP2040 case is only one branch. AEL needs the same front-door discipline for
many user intents:

- detect a target and identify the MCU
- flash known firmware
- run a Golden Suite
- run a specific UART, GPIO, SPI, ADC, mailbox, or blink test
- answer "what can this board do?"
- answer "what resources does this board/instrument expose?"
- explain wiring, ports, channels, and expected observations
- adapt a known test to a close MCU family
- bring up a new board and then promote the successful result into a reusable
  reference

These tasks should not each become isolated agent habits. They should be
classified through a common entry layer and routed into existing AEL mechanisms.

## Proposed Task Classification

A first practical classification can be small:

| User intent | Front-door branch | Primary AEL source |
|---|---|---|
| "Detect this MCU" | `detect_target` | board configs, instrument configs, Golden Reference when known |
| "Flash blink" | `flash_known_firmware` | Golden Reference, board flash config, test plan |
| "Run Golden Suite" | `run_suite` | packs, Golden Suite records, board profile |
| "Run UART/GPIO/etc." | `run_specific_test` | inventory, test plan, board profile |
| "What can this board do?" | `answer_capability_question` | inventory, board resources, packs, docs |
| "What resources are available?" | `answer_resource_question` | inventory, bench resources, instrument surfaces |
| "New similar MCU" | `adapt_reference` | closest-family Golden Reference plus explicit adaptation record |
| "New board bring-up" | `bringup_new_board` | identification gate, closest references, then promotion after success |

This table does not need to be perfect at first. The important point is that
every hardware-facing request enters through classification before execution.

## Required Lookup Order

For each branch, AEL should make the lookup order explicit.

For detect/flash/debug:

1. identify target/instrument family
2. run `ael golden-reference`
3. reuse the referenced board config, pack, skill, and source run
4. only adapt transport binding details unless explicitly creating a new
   reference

For test and suite execution:

1. query inventory for known boards, tests, and packs
2. select an exact board/test if available
3. use closest-family references only with an explicit adaptation label
4. record the resulting successful run as reusable experience

For information questions:

1. query inventory first
2. use board profile and instrument surfaces second
3. use docs and firmware source only when the formal contract is incomplete
4. clearly separate formal facts from inferred implementation details

## Suggested Implementation Direction

The next implementation should be a lightweight task front door, not a large
new framework.

Add a repo-native command such as:

```bash
python3 -m ael task-plan --intent "<natural language or structured intent>"
```

or a structured equivalent:

```bash
python3 -m ael task-plan --task flash --target rp2040 --instrument coreweaver
```

The first version can output a deterministic plan only. It does not need to
execute hardware actions. It should answer:

- classified branch
- target and instrument family
- exact Golden Reference or closest-family reference
- selected board config, test, pack, or inventory source
- allowed execution path
- forbidden ad hoc actions
- missing information that must be resolved before execution

Once stable, `ael run`, `ael pack`, and agent-facing workflows can call this
planner before hardware execution.

## Why Documentation Alone Is Not Enough

Today we already had a document describing the RP2040 flash fix, but the same
mistake still reappeared later in the day. That means documentation is
necessary but insufficient.

The rule must be encoded in a callable AEL entry point. Documentation should
explain the rule, while code should make the correct path the default path.

## Recommended Next Steps

1. Define a small task-intent schema covering the common branches above.
2. Implement `ael task-plan` as a read-only planner that uses Golden Reference,
   inventory, board configs, packs, and docs.
3. Add regression tests for RP2040/CoreWeaver and STM32F103/STM32F401
   ESP32JTAG examples.
4. Teach `ael run` and `ael pack` to optionally emit or consume the task plan.
5. Add AI usage rules requiring agents to call the front door for
   hardware-facing requests.
6. Promote successful new board/test variants into Golden Reference candidates.

## Success Criteria

The front door is working when a future request like:

```text
I connected a new RP2040 board to CoreWeaver. Detect it and flash blink.
```

produces a plan that automatically selects the RP2040 ESP32JTAG/CoreWeaver
Golden Reference and refuses to invent a fresh GDB sequence.

Likewise, a request like:

```text
What can this STM32F401 board do?
```

should route to inventory and board/test coverage, not a manual source-code
search unless the inventory contract is missing data.

The goal is not to eliminate engineering judgment. The goal is to make proven
AEL experience the first input to that judgment.
