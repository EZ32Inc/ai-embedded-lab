# Example Runtime Readiness Family Status v0.1

This note summarizes the current generated-example runtime-readiness state by
family.

It is a compact status view, not a replacement for the catalog.

## RP2 family

### Current state

- generated examples are formally complete enough for normal connection
  retrieval
- current generated examples are mostly blocked by missing runtime bench setup
- ADC paths are additionally blocked by intentionally unbound external analog
  input

### Practical meaning

RP2 example generation quality is good enough to continue, but live runtime
validation should not be claimed until at least one generated example has a real
runtime bench path provisioned.

## STM32 family

### Current state

- generated examples are formally complete enough for normal connection
  retrieval
- current generated examples are mostly blocked by missing runtime bench setup
- STM32 now has a canonical family example-generation skill
- ADC paths are additionally blocked by intentionally unbound external analog
  input

### Practical meaning

STM32 is the strongest family for future generated-example expansion, but the
next runtime-validation step still depends on actual bench setup rather than
more governance work.

## ESP32 family

### Current state

- generated examples are formally complete enough for normal connection
  retrieval
- generated-example runtime claims remain constrained by the current unstable
  meter-backed bench path
- ADC example is also blocked by intentionally unbound external analog input

### Practical meaning

ESP32 generation guidance is usable, but runtime status should stay
conservative until the current meter path is stable enough for more meaningful
live validation.

## Conclusion

The main current limit across families is not missing generation structure.

The main current limits are:

- missing runtime bench setup for RP2 and STM32 generated examples
- unstable bench path for ESP32 generated examples
- intentionally deferred external analog stimulus on ADC examples
