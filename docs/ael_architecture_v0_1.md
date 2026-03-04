AEL Architecture v0.1

AI Embedded Lab (AEL) is an AI-driven hardware validation framework designed to automatically build, run, and verify embedded systems using real hardware.

This document defines the core architecture of AEL v0.1.

Design goals:

deterministic execution

data-driven system behavior

hardware-agnostic core engine

AI-friendly interfaces

easy extension through adapters

1. High Level Architecture

AEL execution pipeline:

CLI / AI Agent
      │
      ▼
Plan Generator
      │
      ▼
RunPlan (data only)
      │
      ▼
Runner (execution engine)
      │
      ├── Build adapters
      ├── Load adapters
      ├── Check adapters
      │
      ▼
Recovery Engine
      │
      ▼
Artifacts + Result Report

The architecture separates planning, execution, and verification.

2. Core Execution Model

AEL uses the following execution model:

PLAN → PREFLIGHT → BUILD → RUN → CHECK → REPORT

Each stage has a clear responsibility.

2.1 PLAN

PLAN determines what will be executed.

Inputs:

board configuration

probe configuration

instrument configuration

test definition

pack definition

Output:

RunPlan

RunPlan is pure data describing the entire run.

2.2 PREFLIGHT

Preflight checks system readiness before execution.

Examples:

compiler availability

debug probe connectivity

instrument readiness

DUT power presence

required tools installed

If preflight fails, execution stops.

2.3 BUILD

Compile firmware or software artifacts.

Examples:

build.idf
build.cmake
build.make

Outputs may include:

firmware.elf
firmware.bin

Build should not depend on DUT hardware state.

2.4 RUN

RUN loads or executes firmware on the DUT.

Examples:

load.openocd
load.esptool
load.daplink

RUN prepares the DUT for validation.

2.5 CHECK

CHECK verifies system behavior.

Examples:

check.uart_log
check.instrument_voltage
check.gpio_signature
check.logic_analyzer

CHECK confirms that the DUT behaves correctly.

2.6 REPORT

REPORT collects artifacts and execution results.

Typical artifacts:

run_plan.json
result.json
uart_log.txt
instrument_measurements.json
build_logs.txt

REPORT provides verification evidence.

3. RunPlan

RunPlan is the central data structure in AEL.

It describes the full execution plan.

Example:

{
  "version": "0.1",
  "inputs": {
    "board_id": "esp32s3_devkit",
    "probe_id": "esp32jtag",
    "instrument_id": "esp32s3_dev_c_meter",
    "test_id": "esp32s3_gpio_signature_with_meter",
    "pack_id": "esp32meter1"
  },
  "selected": {
    "builder": "idf",
    "loader": "esptool",
    "checks": [
      "uart_log",
      "instrument_voltage",
      "digital_signature"
    ]
  },
  "steps": [
    {"name": "build", "type": "build.idf"},
    {"name": "load", "type": "load.esptool"},
    {"name": "check_uart", "type": "check.uart_log"},
    {"name": "check_voltage", "type": "check.instrument_voltage"}
  ]
}

RunPlan is generated before execution and remains immutable during the run.

4. Runner

Runner is the execution engine.

Responsibilities:

execute RunPlan steps

collect artifacts

apply retry and recovery policies

produce result.json

Runner must remain hardware-agnostic.

Runner must NOT contain:

board names

MCU names

tool-specific logic

Hardware behavior must be implemented in adapters.

5. Adapters

Adapters perform actual tool or hardware operations.

Examples:

adapters/build_idf.py
adapters/load_esptool.py
adapters/check_uart_log.py
adapters/check_instrument_voltage.py

Adapter rules:

Adapters MUST:

execute one step

return structured result data

generate artifacts

Adapters MUST NOT:

implement retry loops

perform recovery

modify execution flow

6. Recovery Engine

Recovery is controlled by Runner.

If a step fails, Runner may:

retry step
reset DUT
reconnect probe
rewind execution

Recovery rules are defined in:

docs/recovery_model_v0_1.md

Adapters may provide recovery hints, but recovery actions are executed by Runner.

7. Artifact System

Each run produces a unique directory.

Example:

runs/2026-03-03_11-19-21_esp32s3_devkit_gpio_test/

Artifacts stored may include:

run_plan.json
result.json
uart_log.txt
build.log
instrument_data.json

Artifacts allow runs to be:

audited

replayed

analyzed by AI

8. AI Integration

AEL is designed for AI-assisted development.

AI systems may:

generate RunPlan

analyze result.json

suggest recovery strategies

optimize testing workflows

RunPlan is pure structured data, enabling machine-driven workflows.

9. Core Design Principles

AEL architecture follows several principles.

Data-Driven Execution

Execution is defined by RunPlan, not hardcoded logic.

Separation of Concerns

System layers:

Core Engine
Adapters
Configuration
Artifacts
Hardware Abstraction

Runner never depends on specific hardware.

Adapters encapsulate hardware interactions.

Deterministic Runs

The same RunPlan should produce reproducible results.

AI Compatibility

All outputs are machine-readable.

10. Future Extensions

Possible future capabilities:

distributed hardware testing

multi-board orchestration

automated failure classification

AI-generated RunPlans

simulator integration

Conclusion

AEL architecture separates planning, execution, and verification.

Core components:

RunPlan
Runner
Adapters
Recovery Engine
Artifacts

These components create a scalable platform for AI-driven embedded system validation.
