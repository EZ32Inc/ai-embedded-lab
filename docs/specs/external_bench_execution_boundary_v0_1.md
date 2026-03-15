# External Bench Execution Boundary v0.1

## Purpose

This spec defines the execution boundary that applies when a user's instrument
or bench is external to the current AEL execution environment.

It fills a specific gap: the system previously built firmware successfully and
then incorrectly attempted to run local flash tooling against hardware that was
not attached to the current machine.

## Two Execution Modes

### Mode A: AEL machine-verified

The instrument is reachable from the machine where AEL is running — for
example, `esp32jtag` reachable over the local network.

In this mode AEL can:
- build firmware
- flash via the reachable instrument
- capture GPIO/UART signals
- run automated verification (build → flash → verify pipeline)
- record run evidence in `run_evidence`

### Mode B: External bench (user-local instrument)

The instrument is physically attached to the **user's** bench and is NOT
reachable from the current AEL machine — for example, the user's ST-Link
plugged into their laptop, their own logic analyzer, their own scope.

In this mode AEL can:
- generate or adapt firmware code
- build the firmware locally
- report the artifact path and binary size
- provide the exact flash commands for the user to run on their side
- provide verification instructions (visual, oscilloscope, logic analyzer, etc.)

In this mode AEL must NOT:
- attempt to run `st-flash`, `openocd`, `JLinkExe`, or any other flash tool
  against the user's instrument, which is not attached here
- attempt to connect to, probe, or reset hardware that is not on this machine
- imply that a successful local build means local hardware access exists
- claim that flash or verify succeeded when no such action was taken here

## How To Determine The Execution Mode

Use Mode B when any of the following is true:

- The user states they have a different instrument from the repo reference
  (e.g., "I have ST-Link" when the repo uses esp32jtag)
- The run-gate check returns `instrument_mismatch: true`
- The confirmed instrument is not registered in
  `configs/instrument_instances/*.yaml`
- The user's bench setup differs from the repo bench_setup and no
  remote-access path has been established for their instrument

If in doubt, default to Mode B. It is always safe to stop at
build + instructions.

## Required Response Contract For Mode B (Option B)

When the path is Mode B, the response must follow this contract:

**Step 1 — Build**

Run the build locally. Report:
- build result (success / failure)
- artifact path: e.g., `firmware/targets/stm32f411ceu6/build/stm32f411_app.bin`
- binary size

**Step 2 — Artifact and flash instructions**

Provide the user with:
- the exact artifact file to transfer to their machine (or note it is already
  on their machine if they are working in the same repo)
- the exact command(s) to flash using their instrument
- any required flags or addresses

**Step 3 — Verification instructions**

Provide the user with:
- what to observe or measure to confirm success
- expected behavior (e.g., LED blinks at ~1 Hz, UART prints "OK", etc.)
- if visual: say "verify by visual observation" explicitly

**Step 4 — Stop**

Do not attempt to run flash or capture commands locally.
Do not report "flash succeeded" unless actual flash was confirmed via a
reachable instrument.

## Wording Rules For Mode B Responses

Use:
- "I can build the firmware here."
- "You will need to flash it on your own bench using your ST-Link."
- "Here is the artifact path and the command to run on your side."
- "After flashing, verify by visual observation."
- "Build: success. Binary: `build/stm32f411_app.bin` (980 bytes). Flash on your side."

Do NOT use:
- "Flashing now..." (when no instrument is attached here)
- "Flash successful." (when no flash was performed here)
- "Running openocd..." (when user's instrument is not reachable)
- "Setup complete — ready to verify." (if this implies local hardware access)

## Example: STM32F411 + ST-Link + Visual Verification

User setup:
- Board: WeAct Black Pill (STM32F411CEU6)
- Instrument: ST-Link (user-local, not reachable from this machine)
- LED: PC13
- Verification: visual observation

**Correct Mode B response:**

```
Build: success
Artifact: firmware/targets/stm32f411ceu6/build/stm32f411_app.bin (980 bytes)

Flash on your bench (ST-Link):

  # Option 1 — st-flash
  st-flash write stm32f411_app.bin 0x08000000

  # Option 2 — OpenOCD
  openocd -f interface/stlink.cfg \
          -f target/stm32f4x.cfg \
          -c "program stm32f411_app.bin 0x08000000 verify reset exit"

Verify: after flashing, LED at PC13 should blink at approximately 1 Hz.
Verify by visual observation on your bench.

AEL machine-verified run: not available for this path.
Reason: ST-Link is user-local and not reachable from this machine.
```

**Not acceptable:**

```
Flashing via OpenOCD...
[attempts to run local openocd against user's ST-Link]
Flash complete. Verifying...
```

This is wrong because the user's ST-Link is not attached to this machine.

## Relationship To Adjacent Policies

- `known_board_clarify_first_policy_v0_1.md`: defines when instrument mismatch
  is detected (partial-match evaluation). When instrument mismatch is confirmed,
  execution mode defaults to Mode B.
- `user_project_creation_skill.md`: Option B response structure defined there
  references this boundary.
- Run-gate: a `gate: blocked` result due to instrument mismatch implies Mode B
  is the correct execution path if the user still wants to proceed manually.
