# ST-Link Parallel Default Verification Recovery Skill 2026-03-20

## Purpose

Capture the reusable debug pattern for a local ST-Link path that appears to
break under repeated or parallel `default verification` runs.

## When To Use

Use this skill when all of the following are true:

- the failing path is a local ST-Link bench using `127.0.0.1:<port>`
- ESP32 JTAG or other remote-instrument tests continue to pass
- ST-Link failures include any of:
  - `Found 0 stlink programmers`
  - `Failed to enter SWD mode`
  - `LIBUSB_ERROR_TIMEOUT`
  - `Unsupported Target (Chip ID is 0000000000)`
- the initial suspicion is "parallel default verification is breaking ST-Link"

## Core Rule

Do not treat parallel execution as the root cause until the direct ST-Link
probe path has been isolated.

Parallel runs often reveal the weakness, but the actual failure boundary may be
the local USB-to-SWD attach path.

## Procedure

1. Separate false leads from the real boundary.
   - rerun the non-ST-Link setups individually
   - rerun the ST-Link setup individually
   - if ST-Link still fails alone, stop blaming the batch scheduler
2. Probe below GDB.
   - run direct `st-info --probe`
   - classify the result before changing higher-level orchestration
3. Interpret the probe result.
   - `Found 0 stlink programmers`: local USB/probe visibility problem
   - `Failed to enter SWD mode`: probe sees hardware but target attach is not healthy
   - `chipid 0x000` or unknown target with attach errors: treat as failed SWD attach
   - timeout: treat as transient probe-path failure
4. Harden the adapter, not just the test schedule.
   - launch `st-util` with `--multi` for repeated local use
   - gate startup on a direct probe check
   - add bounded retries for `usb_missing`, `swd_attach_failed`, and `probe_timeout`
5. Revalidate in the correct order.
   - single ST-Link pass
   - back-to-back ST-Link pass
   - full default verification with ST-Link back in the parallel batch
   - repeated full default verification runs

## Evidence Pattern From This Case

False lead:

- "parallel mode is inherently breaking ST-Link"

What separated that from the real cause:

- ST-Link also failed outside the batch
- direct `st-info --probe` reproduced the failure before any GDB session existed
- the signature matched direct attach instability, not test-plan semantics

What fixed it:

- `st-util --multi`
- direct probe gate
- bounded direct-probe retries before GDB-server startup

What proved it:

- repeated single ST-Link passes
- first six-way parallel pass at `2026-03-20_10-33-07`
- three consecutive six-way parallel passes at:
  - `2026-03-20_10-36-49`
  - `2026-03-20_10-37-43`
  - `2026-03-20_10-38-37`

## Implementation Anchor

Primary implementation file:

- [flash_bmda_gdbmi.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapters/flash_bmda_gdbmi.py)

Related execution/config files:

- [default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
- [default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml)

## Anti-Patterns

Do not do these first:

- immediately rewrite default verification scheduling
- assume RP2040/G431 failures and ST-Link failures share one root cause
- stay only at the GDB log layer when direct probe symptoms already exist
- accept one green rerun as closure

## Completion Standard

This pattern is not closed until all of these are true:

- direct-probe failure modes are classified
- the adapter contains the recovery logic
- ST-Link passes back-to-back as a single test
- the full default baseline passes with ST-Link inside the parallel batch
- the result is repeated, not one-off

## Why This Skill Exists

This was easy to misread as an orchestration problem because the visible failure
first became painful inside parallel `default verification`.

The reusable lesson is stricter:

- first isolate the lowest failing boundary
- then harden that boundary
- only after that judge the scheduler
