# Future Improvements

## Bounded helper features

- Digital waveform HTML report:
  add a helper tool that renders captured digital verification data into a local HTML waveform report for human review. Intended for signal-based verification paths such as STM32 GPIO, RP2040 GPIO, STM32 ADC loopback, and similar paths. This should remain a helper/visualization tool and not become part of core verification logic.

- STM32G431CBU6 effective clock root cause investigation:
  the board runs at ~8 MHz effective (SysTick fires at ~500 Hz with RVR=15999, implying ~8 MHz not the expected 16 MHz HSI). All 8 bring-up firmwares were tuned to this observed rate and pass, but the root cause is unresolved. Candidates: HSI default divisor, clock tree configuration in startup, or a board-level factor. Should be investigated before timing-sensitive peripherals are added.

- STM32F1 official-source cache and hardening pass:
  add an STM32F1 official-source fetch/cache path and a bounded hardening pass for STM32F103 generated examples so future STM32F1 capability demos can be cross-checked against official ST source support rather than only repo-local reference code. This should remain a bounded provenance/hardening improvement and not block current STM32F103 capability execution work.
