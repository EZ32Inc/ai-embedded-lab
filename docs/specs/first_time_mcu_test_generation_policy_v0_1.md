# First-Time MCU Test Generation Policy v0.1

This document defines how AEL should generate support for a brand-new MCU or
board that AEL has not previously supported.

## Core statement

For first-time support of a new MCU/board, peripheral implementation must be
anchored primarily in official vendor documentation, SDKs, and official
examples, while test methodology, validation structure, and connection strategy
should be derived primarily from previously validated AEL patterns. Successes,
failures, inferences, and lessons learned must be captured and written back
into the skill/workflow layer.

## Why this policy exists

First-time MCU support is the highest-risk generation case in AEL because two
different kinds of reuse are easy to confuse:

- peripheral implementation reuse
- test methodology reuse

These must stay separate.

The implementation layer is where MCU-specific facts live:

- registers
- startup/runtime support
- clocking model
- memory layout
- peripheral enablement details
- pin multiplexing limits

The methodology layer is where AEL's proven validation patterns live:

- GPIO signature strategy
- UART ready-banner strategy
- staged validation order
- connection-contract shape
- evidence capture expectations

First-time MCU support should reuse methodology aggressively, but should reuse
implementation only when official vendor sources justify it.

## Source priority order

For first-time MCU or board support, use source classes in this order:

1. official vendor primary sources
   - datasheet
   - reference manual
   - official SDK/CMSIS device support
   - official startup/system files
   - official linker/memory templates
   - official vendor examples
2. existing AEL validated methodology
   - staged test shape
   - validation flow
   - evidence model
   - connection strategy patterns
   - previously validated verification criteria
3. existing AEL implementation only as a bounded structural reference
   - file layout
   - naming pattern
   - only when not contradicting official vendor facts
4. explicit inference
   - only when a needed detail is still missing
   - must be labeled as inferred
   - must be recorded as needing verification

## Required separation of sources

Every first-time MCU bring-up must explicitly separate:

- peripheral implementation source
- test methodology source

### Peripheral implementation source

Peripheral implementation should come primarily from official vendor sources.

This includes:

- startup/runtime basis
- CMSIS/device headers
- clock and reset facts
- memory sizes and linker facts
- register field usage
- alternate-function and pin-function constraints
- official example structure for the target peripheral

### Test methodology source

Test methodology should come primarily from previously validated AEL patterns.

This includes:

- which peripheral tests to attempt first
- pass/fail structure
- evidence collection shape
- connection-contract modeling
- proof-signal strategy
- banner strategy
- loopback/self-check strategy
- staged execution order

## Allowed reuse

Allowed:

- reusing official vendor startup/system/CMSIS support directly
- reusing official vendor example categories to decide the safest first
  peripheral path
- reusing AEL test methodology from a validated board such as STM32F103
- reusing AEL file layout, report structure, and plan structure
- reusing AEL naming patterns where they remain device-agnostic

Allowed with explicit justification:

- adapting a local AEL firmware target only after official vendor sources
  confirm that the relevant implementation assumptions still hold
- carrying over a pin choice only after checking the new MCU package/pinout
- carrying over UART defaults only after official source review confirms the
  selected peripheral/pins are valid

## Not allowed

Not allowed for first-time MCU support:

- copying an older MCU target blindly
- treating existing repo code as the primary source of device truth
- carrying over register names, RCC bits, or AF mappings without official
  source confirmation
- carrying over LED pins, boot pins, ADC channels, or UART pins from a
  different MCU family without package-aware verification
- treating a successful methodology on STM32F103 as proof that STM32F411
  implementation details are portable
- collapsing implementation source and validation methodology into one
  justification
- claiming certainty where the source basis is incomplete

## Drift check before code generation

Before any first-time MCU code generation, perform a drift check.

The drift check must answer:

1. What implementation facts are already confirmed by official vendor sources?
2. What implementation facts were inherited from an older AEL board?
3. Which inherited facts have not yet been justified by official sources?
4. Which test methods can be reused safely at the methodology level?
5. Which board/setup assumptions remain unresolved?

Required drift categories:

- device-family drift
- package/pinout drift
- clock-tree drift
- peripheral-instance drift
- alternate-function drift
- memory-layout drift
- bench/setup drift

If drift remains unresolved in a way that affects code generation, generation
should stop or remain explicitly provisional.

## Minimum provenance record

Before code generation starts, record:

- MCU and board identity
- official source set selected
- exact official source paths or documents used
- AEL methodology source selected
- implementation facts still unknown
- assumptions currently inferred
- reasons a reference board was chosen as the methodology basis

## Required result capture after each round

After each meaningful bring-up round, record all of:

- what succeeded
- what failed
- what was inferred
- what was learned

Do not collapse failure into a generic "did not work".

Classify failures at least as:

- official-source gap
- implementation error
- bench/setup mismatch
- unresolved package/pin choice
- methodology mismatch
- runtime instability

## Write-back requirement

Lessons learned from first-time MCU support must be written back into:

- skills
- workflow docs
- policy/spec docs
- target-specific bring-up preparation notes

The goal is not only to finish one board. The goal is to improve future bring-up
quality across AEL.

## Review checklist

Before approving first-time MCU code generation, confirm:

- implementation source is official-first
- methodology source is AEL-pattern-first
- copied local implementation details are explicitly justified
- unresolved drift is visible
- result capture template exists
- lesson write-back path is defined

Before declaring first-time MCU/board bring-up materially complete, also
confirm:

- the validated per-board suite has been rerun after cleanup/fixes
- there is an explicit decision about whether the board should contribute a
  representative baseline step to default verification
- if yes, exactly one low-risk hardware-validated representative step was added
- live default verification was run to prove the new step resolves and executes
- the board is registered as a formal DUT-backed capability
- a closeout note captures the final suite result, default-verification
  decision, and remaining caveats

## Relationship to existing documents

- [dut_target_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/dut_target_generation_policy_v0_1.md)
- [stm32_official_source_generation_policy_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/stm32_official_source_generation_policy_v0_1.md)
- [new_board_bringup_and_validation_flow.md](/nvme1t/work/codex/ai-embedded-lab/docs/new_board_bringup_and_validation_flow.md)
