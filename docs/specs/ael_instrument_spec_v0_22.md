# AEL Instrument Specification v0.22

## One-sentence definition

**An instrument is an external functional entity that can be invoked by Orchestration to perform DUT-related actions, describe its capabilities, and return results.**

---

## 1. Purpose

In AEL, an instrument is used by Orchestration to interact with a DUT in a controlled, machine-usable way.

An instrument is not defined primarily by hardware category (meter, probe, scope, etc.), but by how it participates in the system:

- it can be identified
- it can describe its capabilities
- it can accept instructions from Orchestration
- it can perform DUT-related actions
- it can return results, status, and evidence

---

## 2. Core definition

An instrument is an external functional entity that can be invoked by Orchestration to perform DUT-related actions and return results.

These actions may include:

- observing the DUT
- affecting the DUT
- executing a higher-level task involving the DUT

---

## 3. Required properties of an instrument

An object qualifies as an AEL instrument if it satisfies the following properties.

### 3.1 External to the DUT
The instrument is not part of the DUT itself. It exists outside the DUT and is used by AEL to interact with the DUT.

### 3.2 Callable by Orchestration
The instrument can be selected, addressed, or invoked by Orchestration.

### 3.3 Capability-bearing
The instrument provides one or more usable capabilities relevant to DUT interaction.

Examples:
- observe signal
- measure voltage
- drive signal
- reset target
- flash firmware
- capture data

### 3.4 Action-executing
The instrument can perform one or more actions under Orchestration control.

### 3.5 Result-returning
The instrument returns one or more of the following:
- action result
- observation result
- status
- evidence
- error information

### 3.6 Self-describable
The instrument should be able, directly or via associated metadata/docs, to describe:
- what it is
- what capabilities it has
- how to use those capabilities
- what limitations or requirements apply

This self-description does not need to be natural-language conversational at first. Structured metadata plus documentation is sufficient.

---

## 4. Functional model

An instrument may support actions in these functional categories:

### 4.1 Observe actions
Actions that obtain information from the DUT or DUT environment.

Examples:
- read GPIO level
- capture waveform
- sample voltage
- read UART output
- read debug state

### 4.2 Affect actions
Actions that apply influence, input, or change to the DUT.

Examples:
- drive GPIO
- reset DUT
- set boot mode
- send UART input
- power cycle
- inject signal

### 4.3 Task-level actions
Higher-level orchestrated operations that may internally combine multiple observe/affect steps.

Examples:
- flash firmware
- capture a data session
- run a verification procedure
- acquire and store measurement evidence

These task-level actions are valid instrument actions, but they are built at a higher level than simple observe/affect primitives.

---

## 5. Communication interface

In addition to capabilities, an instrument must define how Orchestration reaches and invokes it.

The communication interface should be kept minimal. It should describe how Orchestration can talk to the instrument, without fully expanding the low-level protocol implementation.

### 5.1 Design principle

**The communication interface describes how Orchestration reaches and invokes an instrument; it does not fully define the underlying transport protocol.**

AEL should treat this as a metadata layer first, not as a new heavy runtime communication abstraction layer.

This keeps the model:
- simple
- implementation-friendly
- broad enough for different instrument styles
- not overloaded with protocol details

### 5.2 Minimum communication metadata

The minimum communication metadata should answer four questions:

1. how does Orchestration reach this instrument?
2. where does it find it?
3. what communication contract is expected?
4. how is it typically invoked?

To support this, an instrument should minimally declare:

- `transport`
- `endpoint`
- `protocol`
- `invocation_style` (optional)

#### transport
The carrier or connection medium used to reach the instrument.

Suggested values:
- `wifi`
- `ethernet`
- `usb`
- `serial`
- `local_process`
- `custom`

Important:
`transport` describes the carrier layer only.
Values such as `http`, `websocket`, or `gdb_remote` should not be treated as transport categories here.

#### endpoint
The address or locator used by Orchestration to reach the instrument.

Examples:
- `192.168.4.1:9000`
- `/dev/ttyUSB0`
- `COM5`
- `local:openocd_instance_1`

The endpoint may remain a simple string in early versions, because its exact format depends on transport.

However, instruments may expose more than one communication surface. Therefore endpoint must **not** be assumed to be scalar-only in all cases.

#### protocol
A stable communication-contract identifier that tells Orchestration what communication behavior is expected.

Examples:
- `gdb_remote`
- `gpio_meter_v1`
- `esp32jtag_web_api_v1`
- `serial_command_v1`
- `http_json_v1`

Important:
`protocol` should not be assumed to be identical to the current runtime adapter/backend name.  
If needed, a separate compatibility field such as `backend` or `runtime_adapter` may be used in configs or implementation-facing metadata.

#### invocation_style
Optional metadata that describes the dominant interaction style.

Suggested values:
- `request_response`
- `stream`
- `command_ack`
- `long_running_task`

In v0.22 this field is descriptive metadata only. It is useful to document expected behavior, but current AEL runtime does not need to rely on it yet.

### 5.3 Communication surfaces

Some instruments expose a single communication surface. Others expose multiple orchestration-facing surfaces.

Examples:
- one surface for flash/debug
- another surface for web control
- another surface for streaming capture

So the communication interface should allow either:

#### Simple form
A single communication description:
- transport
- endpoint
- protocol
- optional invocation_style

#### Structured form
A communication block with one or more named surfaces.

Example shape:
```yaml
communication:
  primary: gdb_remote
  surfaces:
    - name: gdb_remote
      transport: wifi
      endpoint: 192.168.2.63:4242
      protocol: gdb_remote
      invocation_style: request_response
    - name: web_api
      transport: wifi
      endpoint: https://192.168.2.63
      protocol: esp32jtag_web_api_v1
      invocation_style: request_response
      auth:
        type: basic
      options:
        tls_verify: false
```

Notes:
- `primary` is descriptive metadata only. It should not by itself define orchestration routing or capability selection policy.
- per-surface optional metadata such as `auth`, `options`, or transport-specific connection hints is allowed when needed
- the purpose of this structured form is still metadata, not a generic RPC framework

### 5.4 Optional communication metadata

The following may be added later or treated as optional:

- `availability`
- `health_state`
- `notes`
- `backend`
- `runtime_adapter`

Examples of availability/health values:
- `available`
- `busy`
- `offline`
- `unknown`

These are useful, but they are not required for the minimal communication model.

---

## 6. Minimum instrument interface

An instrument should expose, either directly or through config/runtime wrappers, at least the following information:

### Identity
- instrument type/class
- instrument instance name or ID

### Capabilities
- supported actions
- required parameters
- supported targets or limitations

### Communication metadata
- transport
- endpoint
- protocol
- optional invocation style

### Results
- status
- outputs
- evidence/artifacts
- failure information

---

## 7. Non-requirements

The following are not required for something to qualify as an instrument:

- it does not need to be a single-purpose device
- it does not need to be human-facing
- it does not need to have a natural language interface today
- it does not need to be limited to one hardware category
- it does not need to be tied to a “bench” abstraction
- it does not need to fully define its low-level transport protocol inside the spec
- it does not require a new universal communication abstraction layer in AEL runtime

This is important because future instruments may be:
- single-function
- multi-function
- networked
- AI-oriented
- partially virtualized
- custom-built

---

## 8. Future direction

In the future, an instrument may evolve into an **instrument agent**.

That means it may additionally support:

- richer self-description
- queryable descriptive interface
- conversational descriptive interface
- local reasoning about its own capabilities and status

But this is a future enhancement, not a present requirement.

---

## 9. Example 1: Meter

### Why the meter is an instrument

The meter qualifies as an instrument because:

1. It is external to the DUT  
   It is not part of the DUT.

2. It is callable by Orchestration  
   Orchestration can select it and use it during verification.

3. It has usable capabilities  
   For example:
   - measure voltage
   - observe signal state/pattern
   - participate in meter-backed verification

4. It performs DUT-related actions  
   Its primary actions are observe-type actions:
   - read signal behavior
   - sample electrical values
   - provide measurement-based validation

   It may also participate in task-level actions such as:
   - run a meter-backed signature check
   - collect evidence for a golden verification path

5. It returns results  
   It returns:
   - measurement results
   - pass/fail judgments
   - evidence artifacts
   - endpoint/identity information

6. It can be described  
   Its capabilities, endpoint, and usage can be expressed in config and docs.

### Example communication metadata
Simple form:
- transport: `wifi`
- endpoint: `192.168.4.1:9000`
- protocol: `gpio_meter_v1`
- invocation_style: `request_response`

This matches the current AEL meter path more closely than a serial example, while still remaining implementation-light at the spec level.

### Does it fit our definition?
**Yes.**
The meter is a clean example of an instrument because it is an external functional entity that Orchestration uses mainly to **observe** and sometimes to support **task-level validation**.

---

## 10. Example 2: ESP32JTAG

### Why ESP32JTAG is an instrument

ESP32JTAG also clearly qualifies as an instrument.

1. It is external to the DUT  
   It is a separate device used by AEL to interact with the DUT.

2. It is callable by Orchestration  
   Orchestration can resolve a specific ESP32JTAG instance and use it for DUT-related operations.

3. It has multiple capabilities  
   Unlike the meter, ESP32JTAG is a multi-function instrument. Its capabilities may include:
   - flash target via SWD/JTAG-related backend path
   - provide debug/probe connectivity
   - control reset / boot-related lines
   - observe GPIO behavior
   - stimulate GPIO
   - assist in UART/signal tasks depending on configuration

4. It performs both affect and observe actions  
   Examples:
   - affect: reset DUT
   - affect: flash firmware
   - affect: drive signals
   - observe: read target/debug state
   - observe: observe GPIO response

5. It can also perform task-level actions  
   Examples:
   - flash a target image
   - execute a probe-backed verification flow
   - capture or assist in a DUT interaction session

6. It returns results and status  
   It can return:
   - operation success/failure
   - probe identity / endpoint
   - flash result
   - verification outcome
   - evidence paths

7. It can be described  
   Its type, instance identity, endpoint, and supported usage can be documented and modeled.

### Example communication metadata
Structured form:
```yaml
communication:
  primary: gdb_remote
  surfaces:
    - name: gdb_remote
      transport: wifi
      endpoint: 192.168.2.63:4242
      protocol: gdb_remote
      invocation_style: request_response
    - name: web_api
      transport: wifi
      endpoint: https://192.168.2.63
      protocol: esp32jtag_web_api_v1
      invocation_style: request_response
      auth:
        type: basic
      options:
        tls_verify: false
```

### Does it fit our definition?
**Yes.**
ESP32JTAG fits the definition very well. It also shows that an instrument does not need to be single-purpose. It can be a multi-function external functional entity with observe, affect, task-level actions, and one or more explicit communication surfaces.

---

## 11. Final conclusion

Both the meter and ESP32JTAG satisfy the instrument definition.

They differ in complexity and capability mix, but both are:

- external to the DUT
- callable by Orchestration
- capability-bearing
- action-executing
- result-returning
- describable
- reachable through declared communication metadata

That means the definition is broad enough for current AEL instruments, while still structured enough to guide future instrument design.
