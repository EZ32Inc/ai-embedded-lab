# Skills Candidate Catalog

## Purpose

This document is a lightweight catalog of likely AEL skill candidates based on real workflow patterns that are already emerging in the system.

It is not a final skill runtime design.

It is a working reference to help:

- future Codex work
- future Gemini or other model work
- future architecture decisions
- future skill formalization, when the boundaries are stable enough

## What A “Skill” Means In AEL At This Stage

At this stage, a skill in AEL means:

> A reusable structured problem-solving or workflow pattern that an AI can apply to a recurring class of engineering tasks in AEL.

Important clarifications:

- this is not yet a finalized runtime or framework concept
- this is not yet a plugin system or dispatcher design
- this is a lightweight catalog and thinking tool

The value of the skill concept right now is organizational:

- identify repeated engineering patterns
- name them consistently
- clarify their inputs and outputs
- prepare for later formalization without overbuilding too early

## Why Skills Matter, But Should Not Be Overbuilt Yet

Skills matter because AEL already shows repeated patterns in:

- new-board bring-up
- meter setup and selection
- validation summary generation
- recovery and diagnosis
- default verification review

These repeated patterns are useful AI-level units of work.

But overbuilding skills now would be risky because:

- board / test / instrument / bench boundaries are still settling
- instrument architecture has only recently become clearer
- probe-path setup clarity is still less explicit than meter-path setup clarity
- premature formalization would likely lock in unstable interfaces

So the right stance now is:

- keep skills lightweight
- base them on real validated workflow
- let clearer boundaries inform later formalization

## Skill Categories

The current candidate set is easiest to organize into five practical categories:

- board bring-up skills
- workflow/reporting skills
- instrument/setup skills
- verification/debug skills
- recovery/diagnostic skills

## Candidate Skills

### 1. `new_board_bringup`

- category: board bring-up
- purpose: guide a new board from first introduction through first validated run
- trigger / when to use: when adding a new DUT or target family path
- typical inputs: board id, reference board, first intended test path, expected instrument/probe path
- expected output/result: minimal files added, plan executed, readiness summary, known unknowns, recommended next step
- current maturity: obvious candidate
- notes: already strongly informed by [new_board_bringup_and_validation_flow.md](/nvme1t/work/codex/ai-embedded-lab/docs/new_board_bringup_and_validation_flow.md)

### 2. `plan_stage_readiness_summary`

- category: workflow/reporting
- purpose: emit the structured post-`plan` readiness summary
- trigger / when to use: after successful `plan` for new board or uncertain setup
- typical inputs: board, test, instrument profile, endpoint, wiring assumptions, expected checks
- expected output/result: decision-friendly readiness summary with assumptions, unknowns, user inputs needed, safe next step
- current maturity: obvious candidate
- notes: already standardized in current workflow guidance

### 3. `user_correction_and_setup_reprint`

- category: workflow/reporting
- purpose: apply user corrections to board/setup assumptions and reprint the clarified setup
- trigger / when to use: when the user corrects board revision, port, wiring, AP choice, or endpoint assumptions
- typical inputs: correction set, current assumptions
- expected output/result: applied corrections, updated confirmed facts, remaining unknowns, safe next step
- current maturity: obvious candidate
- notes: especially relevant during bring-up and bench setup

### 4. `validation_summary_emission`

- category: workflow/reporting
- purpose: emit concise successful-run summary
- trigger / when to use: after successful run/check/report
- typical inputs: result.json, evidence, key artifacts
- expected output/result: board, test, run id, result, executed stages, key checks passed, artifacts/evidence, caveats
- current maturity: partially emerging
- notes: now partly embodied in the standardized success summary path

### 5. `last_known_good_extraction`

- category: workflow/reporting
- purpose: extract or restate the last-known-good bench state from a successful run
- trigger / when to use: after a pass or before repeating a known-good path
- typical inputs: successful result, current setup facts, bench mapping
- expected output/result: concise LKG setup summary
- current maturity: partially emerging
- notes: now partly embodied in `last_known_good_setup`

### 6. `meter_ap_scan_and_select`

- category: instrument/setup
- purpose: scan visible meter APs and support deterministic selection
- trigger / when to use: when more than one `ESP32_GPIO_METER_XXXX` is visible or when the user asks to choose a meter
- typical inputs: instrument id, Wi-Fi adapter, optional SSID/suffix preference
- expected output/result: visible meter list, selection-required decision, chosen SSID
- current maturity: obvious candidate
- notes: grounded in existing `meter-list` / `wifi-scan` behavior

### 7. `meter_connect_and_ping`

- category: instrument/setup
- purpose: connect to a selected meter AP and confirm the meter is alive
- trigger / when to use: after AP selection or before a meter-based validation run
- typical inputs: instrument id, Wi-Fi adapter, selected SSID or suffix
- expected output/result: connected SSID, endpoint, ping/identity result
- current maturity: obvious candidate
- notes: grounded in existing `wifi-connect`, `meter-ready`, and `meter-ping`

### 8. `instrument_setup_fact_summary`

- category: instrument/setup
- purpose: summarize current selected setup facts such as AP/SSID, endpoint, and port
- trigger / when to use: before a run, after setup changes, or after successful validation
- typical inputs: current setup facts from result or setup commands
- expected output/result: concise current setup summary
- current maturity: partially emerging
- notes: now partly grounded by `current_setup`

### 9. `bench_setup_extraction`

- category: instrument/setup
- purpose: extract the concrete DUT-to-instrument mapping from the active test/config path
- trigger / when to use: before wiring, before run, or when checking assumptions
- typical inputs: test plan, board id, instrument profile
- expected output/result: bench wiring summary with signal/channel mapping
- current maturity: obvious candidate
- notes: strengthened by recent `bench_setup` cleanup

### 10. `gpio_signature_validation`

- category: verification/debug
- purpose: run and interpret GPIO signature validation paths
- trigger / when to use: golden GPIO checks on supported DUTs
- typical inputs: board, test, instrument or probe path
- expected output/result: pass/fail summary plus signal-level interpretation
- current maturity: obvious candidate
- notes: now grounded in both ESP32-C6 and RP2040 validated flows

### 11. `uart_ready_check_interpretation`

- category: verification/debug
- purpose: interpret UART readiness checks and boot-log status
- trigger / when to use: UART token missing, download mode, crash suspicion, or readiness confirmation
- typical inputs: UART capture, expected patterns, observed errors
- expected output/result: readiness decision, likely cause, suggested next action
- current maturity: partially emerging
- notes: already visible in current hardware-check and run triage behavior

### 12. `probe_path_setup_summary`

- category: instrument/setup
- purpose: summarize current probe-side setup and assumptions for JTAG/SWD/LA paths
- trigger / when to use: before or after probe-based runs, especially RP2040/stm32-style paths
- typical inputs: probe config, board wiring, current run result
- expected output/result: concise current setup summary for probe paths
- current maturity: not yet ready
- notes: valuable, but setup facts are still less explicitly grouped here than on the meter path

### 13. `stage_semantics_review`

- category: workflow/reporting
- purpose: check whether stage reporting matches actual execution semantics
- trigger / when to use: after staging changes, plan/preflight behavior changes, or suspicious result output
- typical inputs: result.json, preflight.json, requested stage boundary
- expected output/result: executed/skipped/deferred interpretation and mismatch detection
- current maturity: partially emerging
- notes: motivated by the recently fixed preflight inconsistency

### 14. `default_verification_review`

- category: workflow/reporting
- purpose: interpret the current default verification sequence and summarize baseline health
- trigger / when to use: after `verify-default run`, after sequence changes, or for baseline review
- typical inputs: default verification setting, sequence result, successful run outputs
- expected output/result: concise sequence summary with current baseline status
- current maturity: obvious candidate
- notes: especially useful because default verification is now a real validated baseline

### 15. `intermittent_failure_triage`

- category: recovery/diagnostic
- purpose: triage failures that are not structural but bench/transient in nature
- trigger / when to use: rerun-only failures, transient timeouts, one-off measurement misses
- typical inputs: failed run result, logs, prior passing run, current setup facts
- expected output/result: likely transient-vs-structural assessment and recommended next action
- current maturity: partially emerging
- notes: informed by recent transient meter timeout behavior

## Skills Versus Adjacent Concepts

To keep the catalog clean:

- a skill:
  - a reusable AI workflow/problem-solving pattern

- a workflow document:
  - a human-readable process guide that may inform one or more skills

- a config/schema boundary:
  - a system-structure decision about where data belongs

- an instrument capability:
  - a bench-side function exposed by an instrument, such as `measure.digital`

- a one-off prompt:
  - a single instruction instance, not yet a reusable structured pattern

Skills should consume workflow guidance and architecture boundaries.
They should not replace those concepts.

## Best Near-Term Candidates

The strongest near-term candidates for future formalization are:

### 1. `new_board_bringup`

Why:

- repeated already
- high-value
- strongly guided by an explicit workflow document
- naturally produces structured outputs

### 2. `meter_ap_scan_and_select`

Why:

- recurring real bench task
- already backed by deterministic CLI behavior
- clearly bounded and easy to verify

### 3. `plan_stage_readiness_summary`

Why:

- high leverage for user clarity
- already standardized
- useful across new-board and uncertain-setup cases

### 4. `default_verification_review`

Why:

- current baseline confidence increasingly depends on the default sequence
- useful for both humans and future AI automation

## What Should Wait

The following should probably wait until later:

- a full skill runtime or dispatcher
- deep skill formalization for probe/JTAG setup paths
- large recovery/diagnostic skill formalization
- broad multi-instrument orchestration skills

Why:

- some boundaries are clearer, but not all are equally mature
- probe-path current setup facts are still less explicit than meter-path facts
- premature formalization would likely freeze unstable interfaces

## Summary

This catalog says AEL is at a stage where skills are now clearly emerging from real validated workflow, but should still remain lightweight.

The right current approach is:

- identify recurring high-value patterns
- name them consistently
- ground them in validated workflow and clear boundaries
- formalize only the strongest candidates later, after the surrounding system boundaries are more stable
