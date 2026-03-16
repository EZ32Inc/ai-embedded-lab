# Spec: General Bench Wiring Auto-Discovery v0.1

## Status
Draft

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Motivating Example](#2-motivating-example-stm32g431-bring-up)
3. [Core Principle](#3-core-principle)
4. [Scope](#4-scope)
5. [Goals and Success Criteria](#5-goals-and-success-criteria)
6. [Non-Goals](#6-non-goals)
7. [Channel Model](#7-channel-model)
8. [Inputs](#8-inputs)
9. [Outputs](#9-outputs)
10. [Probe Firmware Requirements](#10-probe-firmware-requirements)
11. [Discovery Methods](#11-discovery-methods)
12. [Inference Logic](#12-inference-logic)
13. [Safety and Policy Constraints](#13-safety-and-policy-constraints)
14. [Default Workflow Integration](#14-default-workflow-integration)
15. [User Interaction Model](#15-user-interaction-model)
16. [Recording Requirements](#16-recording-requirements)
17. [Relation to Skills and Process Capture](#17-relation-to-skills-and-process-capture)
18. [Future Extensions](#18-future-extensions)

---

## 1. Problem Statement

In real bench use, user-provided wiring descriptions are often imperfect.

Typical cases include:

- the wire is physically connected correctly, but the user reports the wrong channel
- the wire is physically connected to a different instrument pin than intended
- multiple lines are connected, but one or more are swapped
- the user only remembers the rough setup, not the exact mapping
- the user gives a partial description and expects the system to infer the rest

If AEL assumes this description is ground truth, it can spend significant time
debugging the wrong problem. What appears to be bad firmware, wrong peripheral
setup, broken test logic, or bad instrument behavior may actually be just a
wiring mismatch.

Therefore, user wiring descriptions should be treated as **helpful hints**, not
guaranteed truth.

---

## 2. Motivating Example: STM32G431 Bring-Up

During STM32G431CBU6 bring-up, an initial observation attempt returned zero
edges on every expected channel (`edges=0, high=0, low=65532`). The assumed
`observe_map` said PA2 → P0.0, but the real connection was PA2 → P0.3.

Because AEL was reading the wrong channel, the firmware and peripheral setup
were initially suspected. The actual problem was a wiring map mismatch.

**Recovery strategy used:** A multi-frequency probe firmware was written that
drove PA2/PA3/PA4/PB3 simultaneously, each at a distinct frequency (ratio
1:2:4:8). All 16 LA channels were captured in one pass. Each toggling channel
was identified by its frequency signature, and the real mapping was inferred:

```
PA2 (fastest)  → P0.3
PA3            → P0.0
PA4            → P0.2
PB3 (slowest)  → P0.1
```

This corrected the `observe_map`. All subsequent tests used the discovered
mapping and passed.

**Lesson:** A higher-information experiment (parallel coded scan across all
channels) resolved in one pass what sequential per-pin debugging would have
taken much longer to find. This motivates making wiring auto-discovery a
general default capability rather than an ad hoc recovery trick.

---

## 3. Core Principle

Before running mapping-sensitive verification, AEL should prefer to:

1. discover the actual observable wiring by experiment
2. infer the real mapping from captured data
3. compare the discovered mapping against the user-provided mapping
4. use the discovered mapping as the operational truth for verification
5. ask the user for confirmation when the discovery contradicts the prior mapping
6. record any discrepancy as part of bench reality and process history

In short:

**Do not assume bench reality. Measure bench reality first.**

---

## 4. Scope

This capability applies whenever test correctness depends on knowing which DUT
signal is connected to which instrument input.

Examples include:

- GPIO signature tests
- GPIO loopback tests
- UART observation
- SPI loopback / signal observation
- PWM observation
- timer capture tests
- EXTI trigger tests
- multi-channel logic analysis
- board bring-up with uncertain observe-map

This capability is especially important during:

- first bring-up of a new board
- first use of a new instrument setup
- remote / assisted operation
- user-reported wiring changes
- any task where the user says "I think I connected it like this"

**Prerequisite:** This capability requires the DUT to be reprogrammable with a
dedicated probe firmware. It does not apply when the DUT is running locked
production firmware or when reflashing is not permitted. See
[Section 10](#10-probe-firmware-requirements).

---

## 5. Goals and Success Criteria

Each goal is paired with a verifiable success criterion.

| Goal | Success Criterion |
|------|-------------------|
| Infer real DUT-to-instrument wiring with minimal user effort | Discovery completes without requiring the user to describe exact pin-to-pin connections |
| Tolerate normal human wiring/reporting mistakes | A wrong or partial user mapping does not cause test failure; the discovered mapping is used instead |
| Avoid wasting debug time on incorrect mapping assumptions | No test failures are attributed to mapping errors when auto-discovery is enabled |
| Produce a usable discovered observe-map for subsequent verification | Downstream verification stages use the discovered mapping, not the user-provided one |
| Make discovery a standard pre-verification phase | Discovery runs automatically on first run for any new board/setup |
| Record discovered mappings and discrepancies as reusable assets | Every discovery run produces a structured record that can be referenced in future sessions |

---

## 6. Non-Goals

This spec does not attempt to solve:

- analog characterization of arbitrary passive networks
- continuous resistance/capacitance measurement
- automatic discovery through power pins or forbidden pins
- unsafe probing of reserved or sensitive channels
- full physical netlist reconstruction of an unknown board

This spec is limited to **safe, observable, digitally inferable connectivity
discovery** within an allowed channel set.

---

## 7. Channel Model

AEL should distinguish channels into the following classes.

### 7.1 Discoverable Channels

Channels that are safe and allowed to be sampled during auto-discovery.

Examples:
- logic analyzer inputs
- general-purpose instrument input channels
- channels listed in the board config `safe_pins` or instrument `discoverable_channels`

**Allowlist source:** The allowlist of discoverable channels is derived from:
1. the board config `safe_pins` field (DUT side)
2. the instrument instance config `discoverable_channels` field (instrument side)
3. any session-level override provided by the user

If no allowlist is configured, discovery must not proceed without explicit user
confirmation of the safe channel set.

### 7.2 Drivable DUT Signals

DUT-side GPIO or other output-capable signals that AEL can intentionally toggle
with known patterns via probe firmware.

### 7.3 Reserved Channels

Channels that must be excluded from auto-discovery.

Examples:
- SWD / JTAG debug pins
- active flash/programming control lines
- UART console lines currently in use
- reset / boot mode pins
- power-related or protection-sensitive lines

Reserved channels must be explicitly listed in the board config or instrument
config and are always excluded, even if the user requests them.

### 7.4 Ambiguous or Conditional Channels

Channels that are only safe under certain conditions. These require a policy
check before inclusion and should default to excluded.

---

## 8. Inputs

The wiring auto-discovery flow may receive any of the following:

### 8.1 Explicit User Mapping
```
DUT PA2 -> P0.0
DUT PA3 -> P0.1
```

### 8.2 Partial User Mapping
```
"PA2/PA3/PA4 are connected somewhere on P0"
"The signal lines should be on P1 or P2"
```

### 8.3 Minimal User Declaration
```
"I connected the board"
"The logic analyzer is connected"
"Please verify before testing"
```

### 8.4 Existing Candidate Observe-Map

Previously known or inferred mapping from config, manifest, history, or prior
runs. This is treated as a candidate to be validated, not as ground truth.

---

## 9. Outputs

The capability should produce:

### 9.1 Discovered Mapping

A structured map of:
- DUT signal → instrument channel
- confidence score per mapping entry
- evidence summary (method, capture parameters, edge counts)

### 9.2 Discrepancy Report

Comparison against user-provided or expected mapping:
- matches
- mismatches
- missing signals (expected but not observed)
- ambiguous signals (multiple candidate channels)
- extra observed signals (toggling channels not in the expected set)

### 9.3 Operational Mapping

The mapping to be used for formal verification in the current run. This is
the discovered mapping unless the user has explicitly overridden it.

### 9.4 Discovery Record

A reusable record including:
- method used
- signals driven and their assigned signatures
- channels sampled
- inferred mapping
- confidence per entry
- mismatch notes
- run context (board, instrument, run id, date)

---

## 10. Probe Firmware Requirements

Both discovery methods require the DUT to run a dedicated probe firmware during
the discovery phase. The following requirements apply.

### 10.1 What Probe Firmware Must Do

- Drive each selected DUT output independently with a controllable, repeatable
  pattern
- Allow per-output frequency or coding assignment via compile-time or
  runtime parameters
- Not interfere with reserved pins (SWD, RESET, BOOT) during operation
- Be flashable via the standard AEL flash pipeline

### 10.2 Minimum Implementation

For parallel coded scan, the firmware must be able to toggle N outputs
simultaneously, each at a distinct frequency ratio. The simplest implementation
uses a SysTick loop with per-output divisors (as used in the STM32G431
probe firmware):

```c
if (++div_a >= 1u) { div_a = 0u; OUTPUT_A ^= 1; }  /* f     */
if (++div_b >= 2u) { div_b = 0u; OUTPUT_B ^= 1; }  /* f/2   */
if (++div_c >= 4u) { div_c = 0u; OUTPUT_C ^= 1; }  /* f/4   */
if (++div_d >= 8u) { div_d = 0u; OUTPUT_D ^= 1; }  /* f/8   */
```

### 10.3 When Probe Firmware Cannot Be Used

If the DUT cannot be reprogrammed:
- Auto-discovery is not available for that session
- AEL must fall back to the user-provided mapping
- A warning should be recorded that the mapping is unverified

---

## 11. Discovery Methods

### 11.1 Method A: One-Wire-at-a-Time Scan

#### Description

Drive one DUT signal at a time while observing all candidate instrument
channels.

#### Procedure

For each selected DUT output:
1. configure only that signal to emit a recognizable pattern
2. keep other outputs inactive or quiet
3. sample all discoverable channels
4. identify which channel shows the matching pattern
5. repeat for the remaining outputs

#### Advantages
- simple and easy to reason about
- robust when channel count is small
- easy to explain to users
- good for debugging or fallback

#### Disadvantages
- slow — requires one capture cycle per DUT output
- less efficient for many signals
- depends on sequential operator attention

#### When to Use
- fewer than 3 DUT outputs to identify
- debugging a single ambiguous channel
- fallback when Method B produces ambiguous results

---

### 11.2 Method B: Parallel Frequency-Coded Scan

#### Description

Drive multiple DUT outputs simultaneously, each with a distinguishable signal
signature, then infer mapping by matching observed channel signatures against
known assignments.

#### Recommended Default Form

Frequency-coded outputs with integer ratio separation:

| Output | Divisor | Relative frequency |
|--------|---------|-------------------|
| A | 1 | f (fastest) |
| B | 2 | f/2 |
| C | 4 | f/4 |
| D | 8 | f/8 (slowest) |

The ratio structure ensures each signal is distinguishable by edge count alone,
without requiring precise frequency measurement.

Other coding forms may also be used:
- duty-cycle coding
- pulse-spacing coding
- time-slot coding
- mixed phase/frequency coding

#### Sampling Constraint

Frequency coding must respect the capture system's Nyquist limit. With a
260 kHz LA sample rate, the maximum reliably detectable toggle frequency is
approximately 100–130 kHz. All coded frequencies must fall well within this
limit. Frequency bands must be spaced far enough apart to avoid aliasing or
misclassification at the edges of each band.

#### Procedure

1. choose the set of DUT outputs to identify
2. assign each output a unique frequency code
3. configure probe firmware with the assigned codes
4. flash probe firmware
5. sample all discoverable channels simultaneously
6. for each channel, compute observed frequency from edge count and window
7. match observed frequency against the known code table
8. infer the real DUT → instrument channel mapping

#### Why This Method Is Preferred

Compared to one-wire-at-a-time scan, parallel coded scan:

- reduces the number of capture cycles to one (or a small fixed number)
- reduces elapsed time
- avoids repeated firmware reconfiguration
- scales to larger channel sets
- is consistent with fully automated bench operation
- is especially valuable when the user may have connected signals across
  multiple ports (P0/P1/P2/P3) and the correct port is unknown

**This is the preferred method** when multiple channels are involved, the
sampling system is reliable, and no safety/policy constraints block parallel
drive.

---

## 12. Inference Logic

### 12.1 Edge Count and Frequency Estimation

For each sampled channel in a capture window of duration `T` seconds:

```
edges = count of 0→1 and 1→0 transitions
freq_hz = (edges / 2.0) / T
```

A channel with fewer than 4 edges is treated as **no signal** (too few
transitions to distinguish from noise or glitches).

### 12.2 Band Matching

Each driven DUT output is assigned a frequency band `[f_min, f_max]` derived
from its coded frequency and a tolerance margin (typically ±30% to account for
LA clock inaccuracy and SysTick drift).

For each sampled channel, find the first band for which:
```
f_min <= freq_hz <= f_max
```

If exactly one band matches → assign the channel to that DUT output.
If no band matches → mark the channel as **no match**.
If multiple bands match → mark the channel as **ambiguous** (see 12.4).

### 12.3 Confidence

Each inferred mapping entry carries a confidence level:

| Confidence | Condition |
|-----------|-----------|
| High | Unique band match, edge count > 20, no competing channel in the same band |
| Medium | Unique band match, edge count 4–20, or one other channel near the band boundary |
| Low | Band match found but edge count is low (4–8) or another channel is close |
| Ambiguous | Two or more channels match the same band |
| No match | No channel matches the expected band for a driven output |

**Decision rules based on confidence:**
- High or Medium → use the discovered mapping automatically
- Low → use the discovered mapping but flag for user review
- Ambiguous → do not use; re-run with a different code set or fall back to
  Method A for the ambiguous outputs
- No match → treat as signal not connected; report to user

### 12.4 Ambiguity Handling

If two or more sampled channels appear to match the same driven signal:
- mark the case ambiguous in the output
- optionally re-run with a different frequency set to break the tie
- optionally fall back to Method A (one-wire scan) for the ambiguous outputs
- report the ambiguity explicitly; do not silently choose one

### 12.5 Missing Match Handling

If no sampled channel matches a driven signal, AEL should consider:
- signal not physically connected
- signal not being emitted as expected (probe firmware issue)
- wrong pin configuration on DUT
- insufficient capture quality or window too short
- driven frequency outside the discoverable channel set's detectable range

AEL should report the missing match explicitly. It must not silently fall back
to the user-provided mapping without informing the user.

### 12.6 Discovery Failure

If discovery cannot produce a usable mapping (too many ambiguous or missing
matches), AEL should:
1. report the failure with the partial results obtained
2. explain which channels were ambiguous or unmatched
3. offer the user three options:
   - re-run discovery with adjusted parameters
   - fall back to user-provided mapping (with a warning that it is unverified)
   - abort and ask the user to check physical wiring before retrying

---

## 13. Safety and Policy Constraints

Auto-discovery must obey bench safety policies.

AEL must not:
- drive or sample channels outside the configured allowlist
- interfere with active debug/programming paths
- disturb boot/reset infrastructure
- assume all instrument channels are always safe to use

The discovery flow must operate only within the safe channel set derived from
board config `safe_pins` and instrument `discoverable_channels`. See
[Section 7.1](#71-discoverable-channels) for allowlist source rules.

Reserved channels must be explicitly excluded and cannot be overridden by
user request.

---

## 14. Default Workflow Integration

### 14.1 Old Workflow

1. user provides mapping
2. AEL trusts mapping
3. AEL runs verification
4. failures may be debugged under false mapping assumptions

### 14.2 New Workflow

1. user provides: exact mapping, rough mapping, or only "I connected it"
2. AEL identifies the safe discovery scope (drivable DUT outputs +
   discoverable instrument channels)
3. AEL checks that probe firmware can be flashed; if not, falls back to
   user-provided mapping with a warning
4. AEL runs wiring auto-discovery (Method B preferred)
5. AEL infers the real mapping and assigns confidence levels
6. AEL compares discovered mapping against user-provided mapping
7. **Confirmation trigger:** AEL asks for user confirmation if:
   - any discovered channel differs from the user-provided mapping, **or**
   - any mapping entry has Low confidence
   - (High/Medium confidence matches with no discrepancy proceed automatically)
8. AEL uses the discovered (and optionally confirmed) mapping for formal
   verification
9. AEL records mapping, confidence, and any discrepancies

### 14.3 When to Run Discovery Automatically

- first run for a new board or new instrument setup
- when the existing observe-map has not been validated on hardware
- when the user states or implies uncertainty ("I think", "I'm not sure")
- when a previous run failed in a way consistent with a mapping mismatch
- optionally skip only when a previously hardware-verified mapping exists and
  is explicitly trusted

---

## 15. User Interaction Model

AEL should support natural user statements such as:

- "I connected it. Please verify."
- "I think these signals are on P1 and P2."
- "Check the wiring first."
- "Confirm what is actually connected."

AEL should respond with:
- the discovered mapping
- confidence per entry
- mismatches against the prior/expected mapping
- a request for confirmation only when there is a discrepancy or low-confidence
  entry (not on every run)

**Example output:**

> Discovery complete.
> Discovered: PA2→P0.3 (high), PA3→P0.0 (high), PA4→P0.2 (medium), PB3→P0.1 (high)
> Discrepancy: your earlier mapping had PA2→P0.0. The discovered mapping differs.
> I will use the discovered mapping for verification. Please confirm or override.

**Example when discovery is clean:**

> Discovery complete. Discovered mapping matches expected observe-map. Proceeding.

---

## 16. Recording Requirements

Whenever auto-discovery runs, AEL should record:

### 16.1 Discovery Context
- board, instrument, run id, date
- selected DUT outputs
- selected discoverable channels
- excluded reserved channels

### 16.2 Method
- which method was used (A or B)
- coding scheme (frequency values, band ranges, window duration)
- capture parameters (sample rate, capture duration)

### 16.3 Results
- discovered mapping with confidence per entry
- observed frequency per matched channel
- unmatched channels and candidate explanations
- ambiguous channels

### 16.4 Discrepancies
If the discovered mapping differs from the user-provided mapping:
- expected mapping
- discovered mapping
- difference summary
- whether user confirmed the discovered mapping
- whether operational mapping was updated

### 16.5 Reuse Classification
The system should mark whether the discovered mapping is reusable for:
- this session only
- this board/instrument pair in future sessions
- proposal to update the verified board config `observe_map`
- skill/rule extraction

---

## 17. Relation to Skills and Process Capture

This capability should be formalized as a reusable skill, not treated as an
ad hoc recovery tool. Each discovery run should capture:

- why discovery was needed (first run, mismatch suspected, user uncertainty)
- what coding method was chosen and why
- what the result changed in the subsequent verification path
- whether the discovered mapping led to a board config update

Wiring misdescription is a **normal human error**, not an exceptional event.
The system should treat it as such: expected, recoverable, and recordable.

Related documents:
- `docs/specs/bringup_process_recording_spec_v0_1.md` — process recording
  requirements for bring-up sessions
- `docs/specs/stm32_cross_family_migration_risk_spec_v0_1.md` — example of
  how unverified assumptions (including wiring assumptions) lead to wasted
  debug time

---

## 18. Future Extensions

- automatic detection of shorts or multi-drop behavior
- confidence-weighted persistence of discovered mappings across sessions
- dynamic discovery across multiple instrument types
- interactive visualization of inferred wiring
- automatic `observe_map` update proposals for board configs
- integration with regression metadata and bench history
- auto-selection of coding patterns based on sampling rate constraints
- support for analog-level signal identification (beyond digital toggling)

---

## One-Sentence Summary

**AEL should treat user wiring descriptions as hints, automatically discover
the real safe observable wiring by coded signal experiments, use the discovered
mapping for verification, and record discrepancies as reusable bench
knowledge.**
