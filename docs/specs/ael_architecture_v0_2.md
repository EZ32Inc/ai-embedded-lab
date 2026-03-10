# AEL Architecture v0.2  
## 6-Part System with Workflow Memory and Skills

## Purpose

This document captures the current architectural view of **AEL (AI Embedded Lab)** after the latest refinement of the Instrument layer and the clarification of Connection.

The goal is to keep the architecture:

- **small**
- **clear**
- **practical**
- **aligned with real AEL code and bench reality**

This version preserves the overall **6-part architecture**, while updating the internal understanding of **Instrument** and clarifying the role of **Connection**.

---

## 1. Recommended Official Architecture

The recommended AEL architecture remains:

1. **AEL Core / Orchestrator**
2. **Instrument**
3. **DUT**
4. **Connection**
5. **Workflow Memory**
6. **Skills**

This remains the right top-level structure.

AEL should still be understood as a system that can:

- **Execute**
- **Remember**
- **Learn**

---

## 2. Why the 6-Part Architecture Still Holds

The original execution foundation remains correct:

- Orchestrator
- Instrument
- DUT
- Connection

These four parts are still the core of real-world execution.

The two additional parts are also still necessary:

- Workflow Memory
- Skills

These are what make AEL more than a one-shot automation tool. They make it possible for AEL to:

- preserve project history
- accumulate engineering evidence
- reflect on what worked and what failed
- extract reusable methods
- improve over time

So the six-part architecture should **not** be expanded casually unless a truly new top-level system part is discovered.

---

## 3. Updated View of Instrument

### 3.1 Definition

An **Instrument** is an external functional entity that can be invoked by Orchestration to perform DUT-related actions, describe its capabilities, and return results.

This includes instruments that primarily:

- observe
- measure
- stimulate
- control
- flash
- debug
- capture
- verify

Examples in current AEL include:
- ESP32JTAG
- meter-style instruments
- future AI-oriented instruments such as logic analyzers, scopes, or multi-function tools

### 3.2 Key idea

Instrument is **not** defined mainly by hardware category.

It is defined by how it participates in AEL:

- it is external to the DUT
- it is callable by Orchestration
- it provides one or more capabilities
- it performs actions
- it returns results, status, and evidence
- it can describe itself through metadata and documentation

### 3.3 Instrument internal structure

At the current AEL stage, Instrument should be understood as including three internal aspects:

#### A. Capability / Action layer
What the instrument can do:
- observe actions
- affect actions
- task-level actions

#### B. Communication access layer
How Orchestration reaches one selected communication surface of the instrument.

Examples:
- ESP32JTAG GDB remote surface
- ESP32JTAG web API surface
- meter TCP surface

This layer is important, but it is considered an **internal part of Instrument**, not a new top-level architecture part.

#### C. Result / Evidence layer
What the instrument returns:
- status
- outputs
- evidence
- failure information

### 3.4 Important architecture decision

AEL should **not** introduce a seventh top-level part for instrument communication access.

Instead:

- instrument communication access belongs **inside Instrument**
- it should be treated as a metadata-first sublayer
- it should not force a heavy runtime communication abstraction too early

This is an important simplification and keeps the six-part architecture clean.

### 3.5 Current AEL code reality

Current AEL implementation already supports the metadata-first direction for Instrument.

In current repo reality, the Instrument area now includes:

- communication metadata on live manifests/configs
- capability-to-surface metadata
- doctor visibility
- inventory visibility
- stage explain visibility
- summary and archive visibility

At the current phase, this remains mostly metadata and reporting support.

It does **not** yet imply:

- generic runtime routing by protocol
- generic runtime routing by invocation style
- a universal communication/session layer
- a heavy transport abstraction rewrite

This architecture document should therefore treat the instrument communication-access layer as a real implemented direction, but still a metadata-first one.

---

## 4. DUT

### 4.1 Definition

DUT means **Device Under Test**.

This is the target embedded board, system, or hardware/firmware platform that AEL is developing, testing, debugging, or validating.

Examples:
- ESP32 boards
- RP2040 boards
- STM32 boards
- Linux SBCs
- FPGA-connected systems
- other embedded targets under development or verification

### 4.2 Role in the architecture

DUT is the object that AEL acts on and reasons about.

It is distinct from Instrument because:

- DUT is the target system
- Instrument is the external system used to observe or affect the DUT

---

## 5. Connection

### 5.1 Definition

**Connection** is the architecture-level relationship between DUT and Instrument.

It defines how the execution-world objects are physically and logically connected.

This includes:

- physical wiring
- pin mapping
- signal roles
- voltage compatibility
- reset / boot / UART / GPIO / JTAG / SWD relationships
- setup constraints
- observation paths
- control paths

### 5.2 Important clarification

Connection in the main AEL architecture refers to the **DUT ↔ Instrument relationship layer**.

It does **not** mean:
- Orchestration reaching an instrument over WiFi / USB / serial
- web API access
- GDB remote access
- TCP endpoint normalization

Those belong to the **Instrument communication access layer**, which is inside Instrument.

### 5.3 Why Connection remains a separate top-level part

Connection remains a top-level architecture part because it describes a **relationship between objects**, not just an internal property of one object.

It is part of the execution-world model and is essential for:
- real hardware setup
- verification accuracy
- automation safety
- structured bench descriptions

---

## 6. Workflow Memory

### 6.1 Definition

Workflow Memory is the system-level layer responsible for recording, organizing, retrieving, and analyzing how work was done across time.

It is more than a simple log.

It should function as:

- process archive
- searchable history
- engineering memory
- reflection input for AI
- evidence base for future skill extraction

### 6.2 Why it must remain a separate part

Workflow Memory spans the entire system.  
It may contain:

- user requests
- plans
- connection definitions used
- instrument actions performed
- DUT versions used
- pass/fail results
- errors and fixes
- workflow outcomes
- historical progression of a project

So it should remain a first-class system part.

---

## 7. Skills

### 7.1 Definition

Skills are reusable operational and engineering methods distilled from experience.

Skills answer:

**What should AEL do next time?**

Examples:
- board/platform skills
- instrument skills
- workflow/diagnostic skills
- troubleshooting methods
- reusable bring-up patterns
- validation and verification methods

### 7.2 Why it must remain a separate part

Skills are not raw history.
They are not the DUT.
They are not only code snippets.

They are reusable methods and patterns that guide future action.

This makes them distinct from Workflow Memory:

- Workflow Memory = history layer
- Skills = method layer

---

## 8. Layered View

A useful way to think about the full architecture is in three stacked layers.

### 8.1 Execution World
These parts directly interact with real hardware:

- DUT
- Instrument
- Connection

### 8.2 Control World
This is the coordination and user-facing control layer:

- AEL Core / Orchestrator

### 8.3 Knowledge World
These parts allow AEL to accumulate and reuse engineering knowledge:

- Workflow Memory
- Skills

This layered view is still valid in v0.2.

The recent instrument refinement does not break it.  
It only makes the Instrument part internally clearer.

---

## 9. Capability Model: Execute, Remember, Learn

The six-part architecture can still be summarized into three major capability groups.

### 9.1 Execution
AEL can do work in the physical world:
- connect to hardware
- flash firmware
- control instruments
- collect signals
- run checks
- verify behavior

Corresponding modules:
- Orchestrator
- Instrument
- DUT
- Connection

### 9.2 Memory
AEL can remember what happened and retrieve it later.

Corresponding module:
- Workflow Memory

### 9.3 Learning
AEL can turn experience into reusable engineering methods.

Corresponding module:
- Skills

This remains one of the clearest ways to explain AEL.

---

## 10. Key Design Decisions in v0.2

### 10.1 Keep the six-part structure
Do not expand to a seventh part for instrument communication access.

### 10.2 Keep Instrument broad but internally clearer
Instrument now explicitly includes:
- capability/action layer
- communication access layer
- result/evidence layer

### 10.3 Keep Connection focused
Connection remains the DUT ↔ Instrument relationship layer.

### 10.4 Treat instrument communication access as metadata-first
This layer should first exist as:
- communication metadata
- capability-surface metadata
- normalized access facts
- doctor/inventory/explain support
- summary/archive visibility

It should **not** force a heavy runtime communication abstraction too early.

### 10.5 Keep Workflow Memory and Skills explicit
They remain first-class system parts and should be shown clearly in docs and diagrams.

---

## 11. Suggested Diagram Logic

A future diagram should explicitly show:

- **Orchestrator -> Instrument**
- **Orchestrator -> DUT**
- **Orchestrator -> Connection**
- **Instrument <-> DUT through Connection**
- **Workflow Memory -> stores workflows, outcomes, context**
- **Workflow Memory -> Skills**
- **Skills -> Orchestrator**

And inside Instrument, a diagram or note may optionally show:

- capabilities/actions
- communication access
- results/evidence

But this should remain an **internal refinement**, not a seventh top-level block.

---

## 12. Why v0.2 matters

This refinement matters because it prevents two common architecture mistakes:

### Mistake 1
Treating instrument communication access as if it were the same thing as Connection.

### Mistake 2
Creating too many top-level parts too early.

v0.2 avoids both mistakes by:

- preserving Connection as the DUT ↔ Instrument relationship layer
- treating instrument communication access as part of Instrument
- keeping the overall architecture small and coherent

This is a better long-term direction.

---

## 13. Short Version

### AEL 6-Part Architecture v0.2

- **AEL Core / Orchestrator** — planning, coordination, control, human-AI interface
- **Instrument** — external functional entity for observe / affect / task-level actions, including instrument-internal communication access
- **DUT** — target board or embedded system under development, test, or verification
- **Connection** — DUT ↔ Instrument wiring, pin mapping, signal roles, voltage compatibility, and setup relationships
- **Workflow Memory** — archive, retrieval, reflection, evidence, history
- **Skills** — reusable engineering methods and operational knowledge

### Core Principle

AEL should be able to:
- **Execute**
- **Remember**
- **Learn**

### Important clarification

- **ConnA** = main architecture-level Connection
- **ConnB** = instrument communication access layer inside Instrument

---

## 14. Final Conclusion

The six-part architecture remains the correct top-level architecture for AEL.

The main refinement in v0.2 is not a new top-level part, but a clearer understanding of Instrument and Connection:

- Instrument has become internally clearer
- Connection remains the real DUT ↔ Instrument relationship layer
- Workflow Memory and Skills remain essential first-class parts

This makes AEL more consistent, more practical, and better aligned with the actual system that is now being built.
