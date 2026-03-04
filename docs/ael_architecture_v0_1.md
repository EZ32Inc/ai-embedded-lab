# AEL Architecture v0.1

AI Embedded Lab (AEL) is designed as an AI-driven embedded development execution platform.

The architecture separates **planning**, **execution**, **hardware interaction**, and **verification** into independent layers so that AI can control and evolve the system safely.

---

# 1. Core Pipeline Model

AEL execution follows a deterministic pipeline:

Plan → Preflight → Build → Load → Check → Report


### Plan
Generate a machine-readable **RunPlan** describing the entire execution.

### Preflight
Verify environment readiness:
- probe connectivity
- required tools
- instrument availability
- configuration validity

### Build
Compile firmware or artifacts.

Examples:

- ESP-IDF
- CMake
- ARM debug build

### Load
Load the firmware or program into target.

Examples:

- esptool
- GDB
- SWD loader

### Check
Observe or measure system behavior.

Examples:

- UART log capture
- GPIO signature verification
- instrument voltage measurement
- logic analyzer analysis

### Report
Produce machine-readable artifacts describing execution results.

Examples:

artifacts/run_plan.json
artifacts/result.json


---

# 2. High-Level Architecture

            +----------------------+
            |      AI / User       |
            +----------+-----------+
                       |
                       v
               +--------------+
               | Orchestrator |
               +--------------+
                       |
                       v
                 Generate RunPlan
                       |
                       v
                +--------------+
                |    Runner    |
                +--------------+
                       |
             Step dispatch via Registry
                       |
                       v
               +----------------+
               | AdapterRegistry |
               +----------------+
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
   BuildAdapters   LoadAdapters   CheckAdapters
        |              |              |
        v              v              v
   Build Tools     Debug/Flash    Instruments
                   Interfaces     Observers


---

# 3. Runner

Runner is the **execution engine of AEL**.

Responsibilities:

- Execute RunPlan sequentially
- Dispatch steps to adapters
- Manage retry and rewind
- Handle recovery actions
- Record artifacts
- Produce result.json

Runner **must remain hardware/tool agnostic**.

Runner does NOT know:

- ESP32
- STM32
- OpenOCD
- esptool
- UART
- instruments

Runner only knows:

step.type


Example:

build.idf
load.gdbmi
check.uart_log


---

# 4. RunPlan

RunPlan is a machine-readable execution plan.

It fully describes the pipeline.

Example structure:

{
"version": "runplan/0.1",
"plan_id": "...",

"inputs": {
"board_id": "...",
"probe_id": "...",
"test_id": "..."
},

"steps": [
{
"name": "build",
"type": "build.idf"
},
{
"name": "load",
"type": "load.idf_esptool"
},
{
"name": "check_uart",
"type": "check.uart_log"
}
]
}


RunPlan is validated via:

schemas/runplan_v0_1.schema.json


---

# 5. Adapter Registry

The Adapter Registry maps **step types** to adapters.

Example:

build.idf → BuildIDFAdapter
build.cmake → BuildCMakeAdapter
load.idf_esptool → EsptoolLoadAdapter
check.uart_log → UARTObserveAdapter


Registry interface:

registry.get(step_type)
registry.recovery(action_type)


The registry isolates Runner from hardware/tool implementations.

---

# 6. Adapters

Adapters implement hardware or tool interaction.

All adapters follow a unified interface:

execute(step, plan, ctx)


Example adapter responsibilities:

### Build Adapter
Compile firmware.

### Load Adapter
Flash or load firmware.

### Check Adapter
Observe or measure behavior.

Examples:

- UART log analysis
- GPIO signal verification
- instrument measurements

Adapters may write artifacts.

---

# 7. Runtime State

Runtime state is stored in:

artifacts/runtime_state.json


It allows adapters to pass information between steps.

Example:

{
"firmware_path": "build/app.elf"
}


---

# 8. Artifacts

Every run produces machine-readable artifacts.

Typical layout:

runs/<timestamp>/

artifacts/
    run_plan.json
    result.json
    runtime_state.json
    uart_log.json
    instrument_voltage.json


These artifacts enable:

- AI debugging
- reproducibility
- automated analysis

---

# 9. Recovery

Recovery allows Runner to automatically repair failed runs.

Example flow:

Check failure
↓
Recovery action
↓
Rewind pipeline
↓
Re-run


Example recovery actions:

reset.serial
power_cycle
reflash


Recovery policy is defined in RunPlan.

---

# 10. Design Principles

AEL architecture follows these rules.

### Hardware abstraction

Core execution must never depend on specific boards.

### Tool isolation

Build/load tools live only in adapters.

### Machine-readable artifacts

All results must be structured data.

### Deterministic pipeline

RunPlan defines the full execution graph.

### AI compatibility

AI can:

- generate RunPlan
- analyze artifacts
- modify code
- trigger reruns

---

# 11. Future Extensions

Possible future extensions include:

- adapter plugin system
- distributed instrument execution
- multi-board orchestration
- simulator integration
- AI-driven recovery strategies

The current architecture already supports these extensions.

