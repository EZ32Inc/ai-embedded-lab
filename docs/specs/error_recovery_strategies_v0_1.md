# Error Recovery Strategies v0.1

## Purpose
This document provides the standard recovery strategy for common hardware and software failures in AEL. It is intended to help the agent diagnose and suggest fixes when a test run fails.

## Common Failures and Recovery Steps

### 1. `ping_fail` (Instrument Unreachable)
- **Problem**: The instrument (e.g., `esp32jtag`) is not reachable over the network.
- **Diagnosis**: 
  - Check if the instrument IP is correct in `configs/instrument_instances/`.
  - Check if the instrument is powered and connected to the same network.
- **Recovery**: 
  - Rerun with `python3 -m ael instruments doctor --id <id>`.
  - If it remains down, ask the user to check power/WiFi.

### 2. `flash_fail` (Flashing Failed)
- **Problem**: The debug probe cannot connect to the target or write the binary.
- **Diagnosis**: 
  - Check SWD/JTAG wiring (VCC, GND, SWDIO, SWCLK, NRST).
  - Verify target power (3.3V).
  - Check for competing GDB sessions.
- **Recovery**: 
  - Perform a physical reset/power cycle.
  - Check if the target is locked (e.g., Option Bytes) and provide unlock commands.

### 3. `verification_miss` (Mailbox/Signal Mismatch)
- **Problem**: The test ran, but the evidence (Mailbox, GPIO frequency) did not match expectations.
- **Diagnosis**: 
  - **Mailbox**: Verify the RAM address in the test plan matches the firmware's linker script.
  - **Signal**: Check if the capture pin is wired correctly according to the test connection config.
- **Recovery**: 
  - Regenerate firmware with more verbose logging.
  - Re-verify the physical connection using `Connection Doctor`.

---

## The Recovery Loop Logic
When AEL detects a failure:
1. **Identify the Stage**: Is it Preflight, Build, Flash, or Verify?
2. **Consult Failure Policy**: Look up the stage-specific recovery in `ael/recovery_policy.py`.
3. **Evidence Extraction**: Capture the last 50 lines of logs and any error summaries.
4. **User Action**: Present the diagnosis and a clear path forward (e.g., "Check wiring on PB13" or "Retry with power cycle").

## Reference
- `ael/failure_recovery.py`: Python implementation of the recovery logic.
- `docs/failure_taxonomy_v0_1.md`: Classification of failure modes.
