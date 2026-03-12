# AEL Local Instrument Interface Refactor Plan v0.1

## 1. Purpose

This document defines the implementation plan for the **current development phase** of AEL.

The goal of this phase is to refactor the **existing instrument network interface** into a stable and well-defined **Local Instrument Interface (Instrument Native API)**.

This local interface will become the **lower layer** of the AEL instrument architecture.

Future **cloud-facing functionality** (registration, sessions, orchestration) will be built **on top of this local layer**, but is **not the primary implementation focus of this phase**.

In short:

```
Current phase goal:
Refactor existing network interface → Local Instrument Interface
```

More precisely for the current repo:

```
Immediate implementation target:
Refactor current local/network-facing instrument paths
into one bounded Local Instrument Interface pilot
```

This refactor must:

* preserve existing working hardware flows
* unify instrument command semantics
* clearly separate native actions from verification logic
* prepare the system for future cloud integration

---

# 2. Scope

This phase focuses only on the **local instrument layer**.

Included:

* refactoring existing network instrument interface
* defining a unified command model
* defining metadata commands
* defining a response/error model
* introducing capability reporting
* separating verification logic from instrument actions

Not included in this phase:

* cloud registration protocol
* cloud authentication
* session routing infrastructure
* multi-user cloud orchestration
* distributed instrument scheduling

Those belong to the **cloud layer**, which will build on the local interface.

### Bounded implementation scope

This phase is **not** a repo-wide migration of every instrument/control-instrument path.

The first practical implementation target should be:

- the existing `usb_uart_bridge_daemon`

The next likely follow-on target may be:

- the meter-facing instrument path

This phase should **not** try to fully normalize the current ESP32JTAG/control-instrument execution path into the same API immediately.

That path is still more adapter/config-runtime driven and should be treated as a later follow-on, not as the pilot target.

---

# 3. Current State

The current repository already contains working instrument functionality.

Examples include:

* flashing firmware to DUT
* capturing GPIO signals
* measuring voltage
* UART communication
* basic device interaction through network services

The current repo also already has important lower-layer building blocks:

* instrument manifests
* capability metadata
* inventory / doctor / resolved instrument views
* one concrete bridge-style network-facing instrument node:
  * `usb_uart_bridge_daemon`

So this phase is not inventing the local layer from zero.
It is normalizing and formalizing patterns that are already partially present.

However, these capabilities currently have several issues:

* command semantics are not unified
* metadata commands are incomplete
* verification logic may be mixed with instrument logic
* capability discovery is not standardized
* response structures may not be consistent

The current network interface therefore behaves more like a set of partially aligned control interfaces rather than one stable **instrument API layer**.

Reasonable current interpretation:

- the USB-UART bridge is the cleanest current native-API candidate
- the meter path is partially aligned
- the control-instrument/JTAG path should not be forced into the first-pass API unification

---

# 4. Target Architecture (Local Layer)

After the refactor, the instrument interface should follow a clear layered structure.

```
AEL System
     ↓
Local Instrument Interface (Instrument Native API)
     ↓
Instrument Implementation
     ↓
Hardware
```

The Local Instrument Interface provides a **stable contract** between:

* AEL orchestration
* verification logic
* gateway/cloud layers
* instrument implementations

This layer must expose **structured commands and responses**.

### First bounded deliverable

The first concrete deliverable for this phase should be:

- one explicit Local Instrument Interface profile
- one real implementation mapped onto that profile
- one durable doctor/status/capability path through existing AEL surfaces

The recommended first implementation is:

- `usb_uart_bridge_daemon`

---

# 5. Local Instrument Interface Responsibilities

The Local Instrument Interface should provide the following categories of commands.

## 5.1 Metadata Commands

These allow the system to discover and understand the instrument.

Required commands:

```
identify
get_capabilities
get_status
doctor
```

Example response:

```
device_type
model
firmware_version
protocol_version
```

---

## 5.2 Core Action Commands

These represent native hardware operations.

Examples should be understood as capability-specific, not universally required across all instruments.

Examples:

```
open
close
read_uart
write_uart
capture_gpio
measure_voltage
```

These commands must perform **only the hardware action**.

They must **not contain verification logic**.

### Important implementation note

For the current phase, avoid treating `flash_firmware` as a required common Local Instrument Interface command.

Reason:

- in current AEL, flash is still often orchestrated through higher-level tool/adaptor paths
- it is not yet a clean common native-instrument action across current families

So the first bounded Local Instrument Interface should focus on:

- metadata
- status/doctor
- capability-native data/control actions

not on forcing every higher-level orchestration action into the first profile.

---

## 5.3 Response Model

All commands must return structured responses.

Success:

```
status: ok
data: ...
```

Error:

```
status: error
error:
  code
  message
  retryable
```

This structure is required for AI-driven orchestration.

---

## 5.4 Capability Model

Each instrument must report capabilities.

Example structure:

```
capabilities:
  flash:
    interfaces: [jtag]

  gpio_capture:
    channels: 8

  uart_monitor:
    ports: 1

  voltage_measure:
    channels: [target]
```

This allows higher layers to reason about instrument capabilities.

For the current repo, this capability model should reuse existing manifest/capability metadata where possible, instead of creating a parallel second capability system.

---

# 6. Refactor Principles

The refactor should follow these principles.

### 6.1 Preserve Working Flows

Existing working hardware flows must continue to function during the refactor.

Avoid breaking:

* flashing
* capture workflows
* current tests

---

### 6.2 Introduce Adapter Layer First

Instead of rewriting instrument logic immediately, introduce an **adapter layer**.

This adapter will expose the new command model while internally calling existing code.

For the current bounded pilot, this means:

- wrap and normalize the existing bridge/instrument implementation
- do not rewrite hardware logic first

---

### 6.3 Separate Verification from Instrument Actions

Instrument commands must perform only:

```
control
capture
measurement
```

Verification logic such as:

```
compare_signature
check_expected_pattern
verify_behavior
```

must move to a higher verification layer.

This is especially important for current meter-backed flows, where verification branching still lives partly in orchestration/runtime code.

---

### 6.4 Avoid Cloud Coupling

The local interface must remain independent from cloud infrastructure.

Specifically, the local interface must **not require**:

```
cloud session
cloud identity
cloud authentication
```

Those belong to the cloud layer.

### 6.5 Do not force full-path unification in this phase

The current phase should not require:

- every manifest-backed instrument
- every bridge daemon
- every control-instrument/JTAG runtime path

to share one fully finished implementation immediately.

The correct approach is:

- establish the lower-layer contract on one bounded pilot
- reuse it where practical
- expand only after the pilot proves out

---

# 7. Current Repo Baseline

Confirmed current baseline:

* `InstrumentRegistry` already exists
* manifest-backed capability metadata already exists
* `instrument_view` and `instrument_doctor` already provide durable inventory/status surfaces
* `usb_uart_bridge_daemon` already provides:
  * stable identity
  * discovery
  * doctor
  * open/close/read/write
  * network-facing API
* meter-backed paths already expose network-facing behavior, but not yet as a normalized common native API
* control-instrument/JTAG paths are still more adapter/config/runtime driven

This means the current repo is already ready for a bounded lower-layer pilot, but not for a broad all-path migration.

---

# 8. Recommended Implementation Order

## Phase 1: Formalize the lower-layer contract

Goals:

* define the Local Instrument Interface / Instrument Native API shape
* define metadata, status, doctor, capability, and response/error model

## Phase 2: Pilot implementation on USB-UART bridge

Goals:

* map the contract onto `usb_uart_bridge_daemon`
* keep compatibility with current bridge behavior
* expose the new contract through existing doctor/view surfaces where practical

Constraint:

* keep the first pilot as bridge-scoped as possible
* avoid unnecessary changes to default-verification runtime paths in this phase

## Phase 3: Selective reuse for meter-facing instrument paths

Goals:

* reuse the same lower-layer ideas where they fit the meter path
* keep verification above the instrument layer

## Phase 4: Reassess control-instrument applicability

Goals:

* evaluate whether any control-instrument/JTAG surfaces should adopt the same lower-layer contract
* do this only after the first pilot is stable

---

# 9. Regression Protection

The USB-UART bridge is the first pilot target, but it must not be allowed to regress the current default-verification path.

Therefore:

## 9.1 Bridge-scoped batches

If a batch changes only:

* `usb_uart_bridge_daemon`
* bridge-local CLI/config/tests
* bridge-specific docs

then targeted bridge tests are sufficient.

## 9.2 Shared-surface batches

If a batch changes shared instrument surfaces such as:

* instrument metadata helpers
* `instrument_view`
* `instrument_doctor`
* registry/manifest interpretation
* any runtime path that could affect active instrument selection or reporting

then the batch must also pass:

```bash
python3 -m ael verify-default run
```

This is the required regression gate for the current repo.

## 9.3 Refactor strategy

The preferred order is:

1. bridge-only normalization first
2. shared-surface integration second
3. default-verification regression check whenever shared code is touched

---

# 10. Success Criteria for This Phase

This phase should be considered successful when:

* one bounded Local Instrument Interface profile is documented
* one real implementation follows it cleanly
* status/doctor/capability retrieval is consistent for that implementation
* verification logic remains outside the native instrument action layer
* no current working hardware flow is broken

---

# 7. Implementation Steps

The refactor should be implemented incrementally.

---

## Step 1: Codebase Mapping

Analyze the current codebase and map existing functionality to the new architecture layers.

Output a mapping table such as:

```
existing function/module → target layer
```

Layers include:

```
instrument native action
verification logic
orchestration logic
```

---

## Step 2: Introduce Adapter Layer

Create a new module:

```
instrument/native/
```

Core components:

```
api.py
command_dispatch.py
response_model.py
capability_model.py
```

The adapter layer will translate structured commands into existing instrument calls.

---

## Step 3: Implement Metadata Commands

Implement:

```
identify
get_capabilities
get_status
```

These should return structured metadata.

---

## Step 4: Implement Core Action Commands

Expose unified commands:

```
flash_firmware
capture_gpio
measure_voltage
read_uart
reset_target
```

Internally reuse existing code where possible.

---

## Step 5: Introduce Response Model

Ensure all commands return standardized responses.

Create helper utilities such as:

```
ok(data)
error(code, message)
```

---

## Step 6: Capability Model

Define capability reporting structure.

Connect it to `get_capabilities`.

---

## Step 7: Verification Audit

Identify functions that belong to verification logic.

Examples:

```
verify_gpio_signature
compare_signature
check_uart_output
```

Mark them for extraction.

---

## Step 8: First Verification Split

Choose one verification path (e.g. GPIO signature verification).

Split it into:

```
instrument: capture_gpio
verification: verify_gpio_signature
```

---

# 8. Deliverables

At the end of this phase, the following should exist:

* Local Instrument Interface adapter
* Unified command model
* Metadata commands
* Capability reporting
* Response/error model
* At least one verification split

---

# 9. Completion Criteria

This phase is considered complete when:

1. AEL can call instruments through the unified local interface.

2. Metadata commands work:

```
identify
get_capabilities
get_status
```

3. Core actions work through the new interface.

4. Existing hardware workflows still function.

5. At least one verification path has been separated from instrument logic.

---

# 10. Relationship to Cloud Layer

This local interface is the **foundation** for future cloud integration.

Future layers will add:

```
instrument registration
session management
remote orchestration
```

Those layers will interact with the system **through the Local Instrument Interface**, not bypass it.

Therefore, the stability and clarity of this local layer is critical for the long-term architecture of AEL.
