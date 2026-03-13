## Regression Anchor Sets

Purpose:
- define the smallest useful rerun sets based on the current stable fixtures and proven paths

### Anchor Set A: Core default baseline
- command shape:
  - `python3 -m ael verify-default run`
- workers:
  - `rp2040_gpio_signature`
  - `stm32f103_gpio_signature`
  - `stm32f103_uart_bridge_banner`
  - `esp32c6_golden_gpio`
- use when:
  - shared runtime
  - shared routing
  - default-verification logic
  - Local Instrument Interface runtime paths
  are touched

### Anchor Set B: Primary sample-board capability baseline
- board family:
  - `stm32f103`
- bounded paths:
  - `stm32f103_gpio_signature`
  - `stm32f103_uart_bridge_banner`
  - `stm32f103_adc_banner`
- use when:
  - capability extension work is centered on one strong sample board
  - a change should be proven beyond the default suite but does not justify multi-family reruns

### Anchor Set C: Secondary family baseline
- path:
  - `rp2040_gpio_signature`
- use when:
  - a change should be checked against a second family baseline
  - but the full 4-worker suite is not required

### Anchor Set D: Bounded path validation
- one explicitly changed path only
- examples:
  - `stm32f103_uart_bridge_banner`
  - `stm32f103_adc_banner`
- use when:
  - the change is clearly isolated to one target/test/instrument path

### Anchor Set E: Health repeat
- command shape:
  - `python3 -m ael verify-default repeat --limit N`
- use when:
  - change risk is about stability, health reporting, locking, or repeatability
- note:
  - keep `N` bounded unless there is a specific reason to extend it
