# Example Connection Contract v0.1

## Purpose

Define the minimum formal connection metadata that generated AEL examples should expose so connection questions can be answered without code inspection.

## Position

This spec extends the existing AEL connection model for generated examples.

It does not replace:

- board `default_wiring`
- board `bench_connections`
- board `observe_map`
- board `verification_views`

It adds the missing test-specific connection facts that often matter for generated examples.

## Minimal Contract Shape

Generated examples should keep using `bench_setup` and may add these fields:

- `serial_console`
- `peripheral_signals`
- `external_inputs`

## Field Definitions

### `bench_setup.serial_console`

Declares the operator-visible serial path for the example.

### `bench_setup.peripheral_signals`

Declares important DUT-local peripheral pins for the example, even when no external bench target is modeled yet.

### `bench_setup.external_inputs`

Declares external stimuli that the example depends on or intentionally leaves undefined.

This makes "missing bench contract" explicit instead of forcing firmware inference.

## Current Audit Summary

### Stronger current formal paths

- Existing golden GPIO paths are already reasonably formal because board `bench_connections` plus `describe-test` answer most connection questions.
- Meter-backed ESP32 paths are stronger because they already use explicit `bench_setup`.

### Previously weak generated-example paths

Before this update, generated UART/ADC/SPI examples were weaker because:

- serial-console expectations lived only in `observe_uart`
- ADC input contracts were not explicit
- SPI bus-role pins were visible only in firmware source

### Current bounded fix

Generated UART/ADC/SPI examples now carry enough explicit test-level contract data for:

- serial console
- key peripheral signals
- ADC external-input gaps

## Current completeness boundary

The generated example set is now good enough to answer normal connection
questions through formal surfaces.

The main remaining intentional gap is not missing retrieval structure. It is
that some examples still declare external stimulus as explicitly unbound. In the
current generated set, this mainly affects ADC examples, although one bounded
first contract-completion step has now been made for `stm32f103_adc_banner`.

That means:

- UART/SPI/I2C examples are generally good runtime-validation candidates when
  the bench path is available
- ADC examples remain formally complete, but some are not yet runtime-ready
  because the external analog source contract is still intentionally undefined
  or defined-but-not-provisioned

There is also a separate bounded case where a formal contract is complete, but
the runtime bench setup is not yet provisioned. In that case, connection
retrieval is still formal and complete, but runtime readiness should be tracked
as blocked by missing bench setup rather than treated as a retrieval gap. The
current `stm32f103_adc_banner` path is the first example of that narrower
blocker class.

## Verification Rule

For generated examples, the connection contract is good enough when:

1. `inventory describe-test` resolves successfully
2. the answer to "what is the connection for this test?" can be given from:
   - `describe-test`
   - the test plan
   - the board profile
3. firmware source is needed only to explain missing contract fields, not to reconstruct the normal answer

## Notes

- This is intentionally a bounded extension, not a broad connection-model rewrite.
- Missing external sources may be declared explicitly as `not_defined`; that is better than leaving them implicit.
- A defined external source may still remain `defined_not_provisioned`; that is a contract-complete but execution-blocked state, not a retrieval gap.
