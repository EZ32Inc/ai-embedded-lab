
# AEL Platform Blueprint (Draft v0.1)

## 1. Vision

**AEL (AI Embedded Lab)** is an open platform where AI can design, build, test, and validate embedded systems automatically using real hardware.

Goal:

Human → describe goal  
AI → implement, build, flash, test  
AEL → validate with real hardware

Long‑term vision:

Autonomous Embedded Development Platform


---

# 2. Core Philosophy

## 2.1 AI‑First

The system is designed primarily for **AI agents**, not traditional human IDE workflows.

Interfaces should be:

- CLI
- JSON
- HTTP
- Git
- Text protocols

Avoid heavy GUI or IDE dependency.



## 2.2 Hardware‑in‑the‑Loop

All validation ultimately comes from **real hardware**.

Flow:

code  
↓  
build  
↓  
flash  
↓  
measure  
↓  
verify



## 2.3 Open Ecosystem

Anyone should be able to contribute:

- board profiles
- test packs
- instruments
- adapters



## 2.4 Safety by Design

AI experimentation must not break the system.

Mechanisms:

- git branches
- gates
- queue system
- reports



---

# 3. AEL Architecture

High‑level architecture:

AI Planner  
↓  
AEL Agent  
↓  
RunPlan  
↓  
Runner  
↓  
Adapters  
↓  
Hardware / Instruments



---

# 4. AEL Components


## 4.1 AEL Core

Minimal execution engine.

Responsibilities:

- run_plan execution
- step orchestration
- retry / recovery
- artifact generation

Modules:

ael/runner.py  
ael/orchestrator.py  
ael/adapter_registry.py  

The core must remain **small and stable**.



## 4.2 AEL Agent

Automation layer enabling AI‑driven development loops.

Responsibilities:

- task queue
- branch worker
- gate validation
- night runs
- report generation

Modules:

ael/agent.py  
ael/queue.py  
ael/reporting.py  

Agent enables:

AI autonomous development loops.



## 4.3 AEL Packs

Reusable **test bundles**.

Example:

packs/  
gpio_signature  
uart_loopback  
adc_accuracy  
pwm_waveform  

Each pack defines:

- build
- load
- run
- check

Uses:

- golden tests
- board validation
- hardware CI



## 4.4 AEL Boards

Board profiles describing target hardware.

Example:

boards/  
stm32f103_bluepill  
esp32s3_devkit  
rp2040_pico  

Board profile includes:

- toolchain
- flash method
- pin map
- clock configuration



## 4.5 AEL Instruments

Measurement hardware used for validation.

Examples:

- logic analyzer
- power monitor
- signal generator
- camera inspection

Interface via:

AIP (AEL Instrument Protocol)



## 4.6 AEL Adapters

Adapters connect Runner to external tools.

Examples:

- build.cmake
- load.openocd
- check.logic_analyzer
- check.shell

Adapters make tools **pluggable**.



---

# 5. AI Development Loop

Core development cycle:

AI writes code  
↓  
Runner builds  
↓  
Flash firmware  
↓  
Instrument captures signals  
↓  
Check results  
↓  
AI analyzes evidence  
↓  
AI modifies code  

Repeat until success.



---

# 6. Task System

Tasks are defined as JSON.

Location:

queue/inbox/task.json

Example task:

generate STM32F103 GPIO demo  
verify with logic analyzer

Agent workflow:

compile task → run_plan  
execute  
validate  
report



---

# 7. Remote Lab (Future)

Enable remote control of AEL labs.

Architecture:

ChatGPT  
↓  
HTTP API  
↓  
AEL Controller  
↓  
Codex  
↓  
AEL Agent  
↓  
Hardware Lab

Users could control labs remotely.



---

# 8. Ecosystem

Open contributions should include:

- boards
- packs
- tests
- instruments
- adapters

The community builds a shared **hardware testing library**.



---

# 9. Long‑Term Vision

Potential future directions:

### Autonomous Firmware Development
AI can design and implement firmware automatically.

### Hardware CI
Every pull request is validated on real hardware.

### Distributed AEL Labs
Multiple labs globally executing tests.

### AI‑Generated Drivers
AI generates and validates hardware drivers automatically.



---

# 10. Project Structure (Draft)

ael/  
runner  
agent  
queue  
reporting  
adapter_registry  

boards/  
packs/  
tests/  
instruments/  
adapters/  

tools/  

docs/



---

# 11. Development Philosophy

Focus on:

- simplicity
- automation
- AI compatibility
- hardware validation

Avoid:

- complex frameworks
- heavy IDE dependency



---

# 12. Guiding Principle

AEL should enable:

AI + hardware = autonomous engineering
