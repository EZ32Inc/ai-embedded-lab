# AEL Failure Taxonomy v0.1

## Purpose

This document defines the standardized failure classification model for AEL.

The goal is:

- Replace free-form error strings with structured error types
- Enable deterministic recovery strategies
- Enable AI reasoning over failure patterns
- Accumulate embedded engineering knowledge in structured form

Every failure in AEL must map to one of these categories.

---

# Top-Level Failure Domains

Failures are classified into 5 primary domains:

1. BUILD
2. FLASH
3. OBSERVE
4. VERIFY
5. INFRASTRUCTURE

Each domain has specific subtypes.

---

# 1. BUILD Failures

Failure during firmware build stage.

### BUILD.COMPILER_ERROR
Compilation failed (syntax, missing symbol, etc.)

### BUILD.CONFIG_ERROR
Invalid configuration, missing target, wrong SDK setup

### BUILD.TOOLCHAIN_NOT_FOUND
Compiler or required build tool not installed

---

# 2. FLASH Failures

Failure during firmware flashing stage.

### FLASH.PORT_NOT_FOUND
Serial/SWD port does not exist

### FLASH.PERMISSION_DENIED
Port exists but permission denied

### FLASH.CONNECTION_FAILED
Cannot communicate with target

### FLASH.TIMEOUT
Flash operation exceeded timeout

### FLASH.UNSUPPORTED_TARGET
Tool cannot recognize target

---

# 3. OBSERVE Failures

Failure during runtime signal observation (UART, GPIO, voltage).

### OBSERVE.UART_PORT_NOT_FOUND
UART device missing

### OBSERVE.UART_PERMISSION_DENIED
UART permission problem

### OBSERVE.UART_OPEN_FAILED
Failed to open serial port

### OBSERVE.DOWNLOAD_MODE_DETECTED
Target stuck in bootloader download mode

### OBSERVE.NO_OUTPUT
UART opened but zero bytes received

### OBSERVE.CRASH_DETECTED
Guru meditation / hard fault / panic detected

### OBSERVE.REBOOT_LOOP
Repeated boot pattern detected

---

# 4. VERIFY Failures

Logical verification failed.

### VERIFY.EXPECT_PATTERN_MISSING
Expected string not found

### VERIFY.FORBIDDEN_PATTERN_FOUND
Forbidden string detected

### VERIFY.GPIO_MISMATCH
Digital signal does not match expectation

### VERIFY.VOLTAGE_OUT_OF_RANGE
Measured voltage outside threshold

### VERIFY.SIGNATURE_MISMATCH
Instrument digital signature mismatch

---

# 5. INFRASTRUCTURE Failures

System-level failures not related to DUT logic.

### INFRASTRUCTURE.CONFIG_INVALID
Invalid profile or test spec

### INFRASTRUCTURE.ADAPTER_EXCEPTION
Unhandled exception inside adapter

### INFRASTRUCTURE.ARTIFACT_WRITE_FAILED
Cannot write output files

### INFRASTRUCTURE.INTERNAL_STATE_ERROR
Orchestrator state machine inconsistency

---

# Error Structure Standard

All failure outputs must include:

```json
{
  "ok": false,
  "error_type": "OBSERVE.DOWNLOAD_MODE_DETECTED",
  "error_summary": "Target is in download mode",
  "domain": "OBSERVE",
  "recovery_attempted": true,
  "recovery_method": "rts",
  "artifacts": [...]
}
