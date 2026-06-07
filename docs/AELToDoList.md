# AEL To-Do List

Future tasks, investigations, and open issues.

Add new items here. Mark completed items with `[x]`, the completion date, and
the commit that closed the work.

---

## Open Investigations

### INV-001 - ESP32JTAG/BMDA SWD State Corruption After Failed Connections

**Status:** [ ] Needs investigation

**Core issue:**
The ESP32JTAG BMDA firmware appears to have a failure-recovery bug. After a
failed GDB connection, SWD scan failure, or attach failure, the internal BMDA
SWD state machine can become unusable. Subsequent connections fail until the
ESP32JTAG probe is restarted.

There is still an open question: the target board may also enter a bad SWD
state. In some cases both the ESP32JTAG probe and the target board may need a
restart before SWD recovers.

**Observed behavior:**

1. AEL `ael pack` flash resilience attempts run sequences such as:
   - `monitor a`, or later `monitor swdp_scan`, with repeated fast failures
   - `monitor connect_srst enable`, which ESP32JTAG reports as unsupported
2. After repeated failed GDB connect/disconnect cycles, the SWD state machine
   appears corrupted.
3. Manual `monitor swdp_scan` also fails afterward. Recovery has required
   restarting ESP32JTAG and sometimes the target board.

**Possible root causes:**

- ESP32JTAG BMDA v2.0.0-rc2 does not fully reset its SWD state after repeated
  failed `swdp_scan` attempts.
- The target STM32 SWD interface may enter a lockup state under some failure
  conditions.
- `monitor connect_srst enable` is unsupported and may still perturb internal
  probe state.

**Investigation steps:**

- Restart only ESP32JTAG, without restarting the target board, and check whether
  SWD recovers.
- Restart only the target board, without restarting ESP32JTAG, and check whether
  SWD recovers.
- Inspect the BMDA ESP32JTAG source path for `swdp_scan` failure handling.
- Reproduce with 10 or more intentionally failed `monitor swdp_scan` attempts.

**Known mitigations:**

- ESP32JTAG can be soft-restarted through
  `POST https://<probe-ip>/set_credentials` while preserving the original
  parameters.
- Board configs can set `allowed_strategies: ["normal"]` to skip
  `connect_under_reset` and avoid sending `monitor connect_srst enable`.
- `flash_bmda_gdbmi.py` should check specific load-failure keywords instead of
  relying on `"failed" not in output`.

---

## Open Tasks

### TASK-001 - ESP32JTAG Direct Restart Command

**Status:** [ ] Needs implementation

Add a direct ESP32JTAG restart action so users do not need to manually power
cycle the probe.

**Background:**
The current soft-restart mechanism uses
`POST https://<probe-ip>/set_credentials` with the existing pbcfg parameters.
This path is already used internally by `_ProbeSoftResetRecoveryAdapter`, but
there is no direct user-facing command.

**Expected behavior:**

- CLI: add a command such as `ael probe restart <probe-ip>`.
- Optional Web UI: add a probe-management restart action if the Web UI remains
  in scope.
- After restart, wait for the GDB port to recover and print a clear success or
  failure status line with elapsed time.

### TASK-002 - Local GDB/OpenOCD Session Isolation For Multiple Probes

**Status:** [ ] Needs implementation

Current local ST-Link and DAPLink session management primarily identifies
sessions by `127.0.0.1:<port>`. With multiple local probes attached, AEL can
reuse or terminate the wrong debug session.

**Risks:**

- Reusing a session for the wrong probe or board.
- Failing to start a new session because a stale port is occupied.
- Flashing or identifying the wrong target.
- Cleanup terminating a debug session that does not belong to the current run.

**Direction:**

- Bind sessions to stable probe identity, preferably USB serial, with USB
  bus/device path as fallback.
- Store runtime ownership as `(probe identity, port, pid, owner, target)`.
- Reuse only when the saved identity matches the current probe.
- Cleanup only sessions started by the current run.
- Select DAPLink/OpenOCD probes precisely instead of relying on the first
  enumerated CMSIS-DAP device.

### TASK-003 - Remove Legacy Board-Agnostic Firmware Target Directories

**Status:** [ ] Needs implementation; coordinate with test-plan cleanup

`firmware/targets/` still contains historical directories that do not include a
specific board ID. These have been replaced by concrete board-specific targets.

| Legacy prefix | Replaced by |
|---|---|
| `stm32f103/` | `stm32f103c6/` and `stm32f103rct6/` |
| `stm32f407/` | `stm32f407vet6/` |
| `stm32f401/` | `stm32f401rct6/` |
| `stm32f411/` | `stm32f411ceu6/` |
| `stm32g431/` | `stm32g431cbu6/` |

**Execution order:**

1. Confirm there are no active references from `tests/plans/` or `packs/`.
2. Remove the legacy firmware target directories.
3. Remove matching legacy test plans.
4. Verify all current packs still resolve and run as expected.

### TASK-004 - CH32V003 Recovery And `pwr_sleep` AWU Fix

**Status:** [ ] Needs hardware recovery and validation

The `pwr_sleep` firmware used `__WFE()` without configuring
`EXTI->EVENR bit9`. The board can remain stuck in sleep, leaving the WCH-Link
SDI path unresponsive and preventing new firmware flashes.

The test has been removed from `ch32v003_golden.json`; the current golden suite
is 13/13.

**Recovery path:**

1. Use WCH-LinkUtility in ISP mode.
2. Select CH32V003 through the WCH-Link USB connection.
3. Write any known-good running firmware, for example
   `ch32v003_minimal_mailbox.elf`.
4. Verify:

```bash
ael run --test tests/plans/ch32v003_minimal_mailbox.json
```

**Fix direction:**

The corrected firmware should:

- set `EXTI->EVENR |= (1u << 9)` so AWU events can wake WFI
- use `__WFI()` for a single short sleep
- write PASS after wake
- enter a busy liveness loop so debug halt remains reliable
- update liveness detail through `SysTick->CNT >> 13`

After recovery:

```bash
ael run --test tests/plans/ch32v003_pwr_sleep.json
```

If the test passes, add `pwr_sleep` back to `ch32v003_golden.json` and restore
the golden suite to 14/14.

**Related follow-up:**
Nine CH32V003 stage-2 tests previously passed, including I2C, SPI DMA, ADC DMA,
and TIM DMA. After recovery, rerun them before deciding whether they should join
the golden suite or remain an independent pack.

---

## Done

No completed items recorded in this file yet.
