# ESP32JTAG Optional Lifecycle Surface Review

Date: 2026-03-19

## Purpose

Review which optional lifecycle-oriented surfaces would make sense for
`ESP32JTAG` after the current runtime-facing instrument API work.

## Candidate Surfaces

### 1. Service Reachability Summary

Potential value:

- summarize `gdb_remote` and `web_api` availability in one short report
- help users distinguish "bench reachable" from "bench healthy"

Recommendation:

- useful
- could stay as a formatting/presentation addition rather than a new command

### 2. Endpoint-Specific Status Detail

Potential value:

- expose endpoint-specific latency or retry state
- make it easier to explain "doctor ok but one endpoint flaky"

Recommendation:

- useful
- lower risk than adding restart/provision actions

### 3. Recovery Hint Surface

Potential value:

- return structured recovery hints such as:
  - check another debugger session
  - power-cycle ESP32JTAG
  - verify Wi-Fi reachability

Recommendation:

- useful as doctor/status enrichment
- should not be implemented as a restart action by default

### 4. Service Restart Action

Potential value:

- recover stuck probes faster

Recommendation:

- do not add yet
- too close to provision/recovery ownership
- should only be added with a very clear operational contract

### 5. Provision / Firmware Update Actions

Potential value:

- could eventually unify more lifecycle handling

Recommendation:

- keep out of scope for now
- not needed to complete the current instrument API phase

## Recommendation

If follow-on work is needed, the best order is:

1. better status/detail presentation
2. structured recovery hints
3. only then consider whether any active lifecycle action is really justified
