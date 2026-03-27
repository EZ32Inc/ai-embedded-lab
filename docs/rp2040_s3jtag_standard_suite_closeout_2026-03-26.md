## RP2040 S3JTAG Standard Suite Closeout

Date: 2026-03-26

Scope:
- Pack: `packs/standard_rp2040_s3jtag.json`
- Board profile: `configs/boards/rp2040_pico_s3jtag.yaml`
- Instrument instance: `configs/instrument_instances/s3jtag_rp2040_lab.yaml`
- New test plans:
  - `tests/plans/rp2040_minimal_runtime_mailbox_s3jtag.json`
  - `tests/plans/rp2040_gpio_level_low_with_s3jtag.json`
  - `tests/plans/rp2040_gpio_level_high_with_s3jtag.json`
  - `tests/plans/rp2040_gpio_signature_100hz_with_s3jtag.json`
  - `tests/plans/rp2040_gpio_signature_with_s3jtag.json`

Bench shape validated:
- `S3JTAG GPIO4` -> `RP2040 SWCLK`
- `S3JTAG GPIO5` -> `RP2040 SWDIO`
- `S3JTAG GPIO15 TARGETIN` <- `RP2040 GPIO18`
- common `GND`
- no additional UART, SPI, ADC, or reset wiring

Result summary:
- `rp2040_minimal_runtime_mailbox_s3jtag`: PASS
- `rp2040_gpio_level_low_with_s3jtag`: PASS
- `rp2040_gpio_level_high_with_s3jtag`: PASS
- `rp2040_gpio_signature_100hz_with_s3jtag`: PASS
- `rp2040_gpio_signature_with_s3jtag`: PASS
- formal pack `packs/standard_rp2040_s3jtag.json`: PASS

Successful run ids:
- `2026-03-26_07-44-49_rp2040_pico_s3jtag_rp2040_minimal_runtime_mailbox_s3jtag`
- `2026-03-26_07-44-59_rp2040_pico_s3jtag_rp2040_gpio_level_low_with_s3jtag`
- `2026-03-26_07-45-18_rp2040_pico_s3jtag_rp2040_gpio_level_high_with_s3jtag`
- `2026-03-26_07-45-49_rp2040_pico_s3jtag_rp2040_gpio_signature_100hz_with_s3jtag`
- `2026-03-26_07-46-20_rp2040_pico_s3jtag_rp2040_gpio_signature_with_s3jtag`

Key evidence:
- Mailbox runtime gate proved the SWD flash + attach path without depending on `TARGETIN`:
  - `runs/2026-03-26_07-44-49_rp2040_pico_s3jtag_rp2040_minimal_runtime_mailbox_s3jtag/result.json`
  - `runs/2026-03-26_07-44-49_rp2040_pico_s3jtag_rp2040_minimal_runtime_mailbox_s3jtag/artifacts/mailbox_verify.json`
- Static-state signal validation proved `TARGETIN` can be used for digital level checks, not only toggles:
  - `runs/2026-03-26_07-44-59_rp2040_pico_s3jtag_rp2040_gpio_level_low_with_s3jtag/artifacts/verify_result.json`
  - `runs/2026-03-26_07-45-18_rp2040_pico_s3jtag_rp2040_gpio_level_high_with_s3jtag/artifacts/verify_result.json`
- Frequency-band signal validation proved both slower and faster toggle cases on the same one-wire verify path:
  - `runs/2026-03-26_07-45-49_rp2040_pico_s3jtag_rp2040_gpio_signature_100hz_with_s3jtag/artifacts/verify_result.json`
  - `runs/2026-03-26_07-46-20_rp2040_pico_s3jtag_rp2040_gpio_signature_with_s3jtag/artifacts/verify_result.json`

What had to change:
- AEL `TARGETIN` handling previously assumed success only meant `state=toggle`. That was too narrow for a standard suite, because `steady high` and `steady low` are also valid outcomes.
- The signal-verification path was extended so tests can declare `expected_state` and `TARGETIN` checks can pass for `high`, `low`, or `toggle` according to the plan.
- New RP2040 golden assets were added for `low`, `high`, and `100 Hz` variants so the suite does not overfit to the earlier `1 kHz` smoke-only path.

Observed transient behavior during live validation:
- On the first capture attempt after flashing, `TARGETIN` occasionally reported an early unstable or low-frequency reading before settling to the expected final state/frequency.
- The final passing runs showed correct end-state measurements:
  - low: `state=low transitions=0 estimated_hz=0`
  - high: `state=high transitions=0 estimated_hz=0`
  - 100 Hz: `state=toggle estimated_hz=99`
  - 1 kHz: `state=toggle estimated_hz=999`
- This indicates the path is valid, but initial post-flash sampling can land in a startup window. The closeout conclusion should be based on the final run artifacts, not the first transient sample line.

Conclusion:
- `S3JTAG` now has a real `standard` no-extra-wire RP2040 suite, not just a single smoke case.
- The validated scope is now:
  - SWD flash and attach
  - mailbox runtime gate
  - steady low/high digital verification on `TARGETIN`
  - slower toggle verification at `100 Hz`
  - faster toggle verification at about `1 kHz`
- This is the correct baseline before attempting UART, SPI, or ADC expansion.
