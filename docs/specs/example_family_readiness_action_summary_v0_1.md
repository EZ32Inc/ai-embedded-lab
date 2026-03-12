# Example Family Readiness Action Summary v0.1

## Purpose

This note is a compact operator-facing summary of the current generated-example
state by family.

It answers:

> For each current family, what is the dominant readiness state, what is the
> main blocker, and what is the next allowed action?

Use this as a quick reference. The authoritative source of detailed per-example
status remains:
- [example_generation_catalog_v0_1.json](/nvme1t/work/codex/ai-embedded-lab/docs/specs/example_generation_catalog_v0_1.json)

## Summary Table

| Family | Current dominant readiness | Main blocker | Next allowed action |
| --- | --- | --- | --- |
| STM32 | `blocked_missing_bench_setup` | generated UART/SPI/I2C runtime paths are not bench-provisioned yet | keep plan/build claims, wait for bench provisioning before live runtime validation |
| RP2 | `blocked_missing_bench_setup` | generated UART/SPI/I2C runtime paths are not bench-provisioned yet | keep plan/build claims, wait for bench provisioning before live runtime validation |
| ESP32 | `blocked_unstable_bench_path` | current meter-backed bench path is unstable enough to distort repeatability | keep runtime claims conservative; bounded live attempts only as bench observations |
| Cross-family ADC | `blocked_unbound_external_input` | external analog-source contract is intentionally not defined yet | define and provision the analog input contract before promoting runtime claims |

## Interpretation

### STM32

STM32 generated examples are in relatively good structural shape:
- formal connection contract is present
- plan/build validity is present

But current generated-example runtime validation is mostly blocked by missing
bench provisioning rather than generation quality.

### RP2

RP2040 and RP2350 generated examples are also structurally good:
- formal connection contract is present
- plan/build validity is present

Like STM32, they are mostly blocked by missing runtime bench provisioning for
the generated UART/SPI/I2C paths.

### ESP32

ESP32 generated examples remain useful generation outputs, but their runtime
path is currently more limited by the unstable meter-backed bench dependency
than by generation quality.

### ADC

ADC examples across families should remain conservative:
- they are formally answerable for connection questions
- but stronger runtime claims should wait until a real external analog-source
  contract is defined and provisioned

## Use With

- [generated_example_runtime_readiness_review.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/generated_example_runtime_readiness_review.md)
- [generated_example_next_action_selection.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/generated_example_next_action_selection.md)
- [next_example_expansion_decision_v0_1.md](/nvme1t/work/codex/ai-embedded-lab/docs/specs/next_example_expansion_decision_v0_1.md)
