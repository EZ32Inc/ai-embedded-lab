# Example Generation Gap Review 2026-03-11

This document records the current repo-level gap review for generated example
support after the first bounded UART/ADC/SPI/I2C expansion batch.

It is a planning and status document, not a family policy.

## Scope

This review covers the current generated-example path for:

- RP2 family
  - RP2040
  - RP2350
- STM32 family
  - current bounded review based on STM32F103 example generation
- ESP32 family
  - current bounded review based on ESP32-C6 example generation

## Confirmed current state

### Repo-level generation support

The repo now has:

- repo-level example generation policy
- family-specific example generation policy for:
  - ESP32
  - RP2
- STM32 target-generation policy and STM32 target catalog
- generated UART/ADC/SPI/I2C example paths for:
  - RP2040
  - STM32F103
  - ESP32-C6
- generated GPIO/UART example paths for:
  - RP2350
- a formal connection-contract retrieval rule
- generated example plans that now answer connection questions through:
  - `inventory describe-test`
  - plan metadata
  - board profile metadata

### Formal contract coverage

For the currently generated UART/ADC/SPI/I2C example set, formal contract
coverage is now consistent enough to answer:

- serial console path
- peripheral signals
- explicit missing external inputs where applicable

without needing firmware inspection in the normal case.

### Build and plan validation

The current generated example set has:

- `inventory describe-test` coverage
- `explain-stage --stage plan` coverage
- build smoke validation

This is strong enough for bounded example expansion work.

## Family review

### STM32 family

Strengths:

- strongest policy base
- family-specific official-source generation policy exists
- STM32 generation catalog exists
- case-study skills exist
- generated STM32F103 example set now covers UART/ADC/SPI/I2C with formal
  connection metadata

Current gaps:

- example generation tracking is still weaker than target generation tracking
- family coverage is still effectively one bounded example-generation baseline
  board (`stm32f103`)
- no STM32-family example-generation skill at the same canonical level as the
  ESP32 and RP2 family skills

Recommended next improvement:

- add a canonical STM32-family example-generation skill or policy note that
  connects official-source target rules to example-generation rules

### ESP32 family

Strengths:

- family-specific example-generation policy exists
- canonical family skill exists
- current ESP32-C6 generated example set covers UART/ADC/SPI/I2C
- ESP32-family method is clear:
  - official ESP-IDF example first
  - AEL-local structure second

Current gaps:

- no ESP32 generation catalog comparable to STM32 target catalog
- example provenance/status tracking is lighter than STM32
- current formal review is effectively centered on `esp32c6_devkit`
- generated examples are build-and-plan validated, but runtime validation is
  still selective and meter-path dependent

Recommended next improvement:

- keep the current family method
- expand runtime validation conservatively
- only add a richer ESP32 catalog if broader family expansion is planned

### RP2 family

Strengths:

- family-specific example-generation policy exists
- canonical RP2 family skill exists
- RP2040 generated example set covers UART/ADC/SPI/I2C
- first RP2350 generated baseline exists
- family method is clear:
  - RP2040 future work: local-reference-first
  - first RP2350 line: official Pico SDK support plus local RP2040 shape

Current gaps:

- no RP2 generation catalog
- RP2350 example set is still light compared with RP2040
- no runtime-validated RP2350 baseline yet

Recommended next improvement:

- keep future RP2040 work local-reference-first
- add one more bounded RP2350 example only when it has clear value
- defer richer RP2 catalog work until broader RP2350 expansion is real

## Cross-family conclusions

### Strong enough now

The repo is strong enough now for:

- bounded cross-family example generation
- plan/build validation
- formal connection-contract answers
- conservative example tracking in the repo-level example catalog

### Still intentionally light

The repo is still intentionally light on:

- broad runtime validation claims for generated examples
- family-wide example catalogs beyond the current repo-level catalog
- USB example generation
- new-vendor family example generation

### Current highest-value gaps

1. selective runtime validation of generated examples
2. a stronger STM32-family example-generation skill
3. broader-family tracking only if expansion widens further

## Recommended next steps

1. runtime-validate a small subset of generated examples
2. add a canonical STM32-family example-generation skill
3. keep USB and new-vendor family expansion separate from the current bounded
   batch
