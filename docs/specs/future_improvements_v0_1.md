# Future Improvements

## Bounded helper features

- Digital waveform HTML report:
  add a helper tool that renders captured digital verification data into a local HTML waveform report for human review. Intended for signal-based verification paths such as STM32 GPIO, RP2040 GPIO, STM32 ADC loopback, and similar paths. This should remain a helper/visualization tool and not become part of core verification logic.

- STM32F1 official-source cache and hardening pass:
  add an STM32F1 official-source fetch/cache path and a bounded hardening pass for STM32F103 generated examples so future STM32F1 capability demos can be cross-checked against official ST source support rather than only repo-local reference code. This should remain a bounded provenance/hardening improvement and not block current STM32F103 capability execution work.
