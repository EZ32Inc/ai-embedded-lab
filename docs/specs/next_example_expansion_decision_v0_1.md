# Next Example Expansion Decision v0.1

This note records the current bounded decision after the first generated-example
runtime-validation governance pass.

## Decision

The next generated-example expansion work should prioritize:

1. readiness-aware next-action selection
2. bounded runtime validation only on examples that are actually runtime-ready
3. defer USB and new-vendor family expansion

That next-action selection should be based on:
- formal connection-contract completeness
- runtime-readiness status
- actual runtime-validation status

For the execution-facing state transitions behind that decision, see:
- [example_runtime_readiness_transition_table_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/example_runtime_readiness_transition_table_v0_1.md)

## Why

### RP2040 and STM32F103 are structurally strong, but not currently provisioned

- their default verification paths are stable enough for repeated use
- their generated UART examples are formally complete
- but the generated UART example runtime paths are currently blocked by missing
  bench setup

### ESP32-C6 remains useful but should stay conservative

ESP32-C6 generated examples remain valid generation examples, but live
runtime-validation claims should remain conservative while current meter-backed
bench instability continues to block or distort attempts.

### ADC examples are not the next validation target

ADC examples are formally complete, but several still intentionally leave the
external analog source undefined. That makes them weaker candidates for the
next runtime-validation batch.

### USB remains a separate higher-risk expansion

USB should remain a separate decision and should not be mixed into the current
bounded validation path.

## Recommended immediate next batch

1. use the runtime-readiness model to choose the next least blocked example path
2. do not attempt live validation on examples blocked by missing bench setup
3. continue with bounded generation/spec work unless or until a real runtime
   path is provisioned

## Out of scope for this decision

- broad USB example generation
- broad new-vendor family generation
- broad runtime validation across all generated examples at once
