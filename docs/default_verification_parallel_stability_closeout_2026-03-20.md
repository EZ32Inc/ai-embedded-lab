# Default Verification Parallel Stability Closeout 2026-03-20

## Scope

This closeout records the live stabilization of parallel `default verification`
after the schema/default-verification changes and the ST-Link recovery work
landed.

The question for this closeout was narrow:

- can the six-test default baseline run in parallel repeatedly
- does the previously unstable ST-Link path now hold inside that parallel batch
- do the schema/execution changes now have real bench evidence behind them

## What Failed Earlier

The blocking instability was not the RP2040 or STM32G431 GPIO-signature tests.
Those failures were transient ESP32 JTAG setup health issues and later recovered.

The durable blocker was `stm32f103_gpio_no_external_capture_stlink`.

Earlier failure signatures showed two layers of problems:

- `st-util` single-session limitations during repeated local use
- direct ST-Link attach failures below GDB, including:
  - `Found 0 stlink programmers`
  - `Failed to enter SWD mode`
  - `GET_VERSION send request failed: LIBUSB_ERROR_TIMEOUT`
  - `ENTER_SWD send request failed: LIBUSB_ERROR_TIMEOUT`

This separated the real issue from the false lead that "parallel default
verification itself is the root cause". Parallel execution exposed the problem,
but the unstable boundary was the ST-Link attach path.

## Changes That Mattered

Relevant implementation changes:

- [ael/adapters/flash_bmda_gdbmi.py](/nvme1t/work/codex/ai-embedded-lab/ael/adapters/flash_bmda_gdbmi.py)
  - run local `st-util` with `--multi`
  - add a direct `st-info --probe` health gate before GDB-server startup
  - classify direct-probe failures as `usb_missing`, `swd_attach_failed`, or
    `probe_timeout`
  - retry those direct-probe failures with bounded backoff before startup
- [ael/default_verification.py](/nvme1t/work/codex/ai-embedded-lab/ael/default_verification.py)
  - add grouped execution support for `mode: sequence`
- [configs/default_verification_setting.yaml](/nvme1t/work/codex/ai-embedded-lab/configs/default_verification_setting.yaml)
  - restore the current default baseline to one parallel batch containing all
    six experiments

Supporting tests passed during the work:

- `PYTHONPATH=. pytest -q tests/test_flash_bmda_gdbmi.py`
- `PYTHONPATH=. pytest -q tests/test_default_verification.py`

## Live Validation Evidence

Single-test recovery and repetition evidence:

- ST-Link pass after direct-probe recovery:
  [result.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-29-16_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)
- back-to-back ST-Link passes:
  [result.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-30-41_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)
  [result.json](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-31-03_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)

First full six-way parallel pass:

- [esp32c6](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_esp32c6_devkit_esp32c6_gpio_signature_with_meter/result.json)
- [rp2040](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_rp2040_pico_rp2040_gpio_signature/result.json)
- [stm32f411](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_stm32f411ceu6_stm32f411_gpio_signature/result.json)
- [stm32g431](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_stm32g431cbu6_stm32g431_gpio_signature/result.json)
- [stm32h750](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_stm32h750vbt6_stm32h750_wiring_verify/result.json)
- [stm32f103 ST-Link](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-33-07_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)

Three consecutive six-way parallel passes:

- run set `2026-03-20_10-36-49`
  - [esp32c6](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_esp32c6_devkit_esp32c6_gpio_signature_with_meter/result.json)
  - [rp2040](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_rp2040_pico_rp2040_gpio_signature/result.json)
  - [stm32f411](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_stm32f411ceu6_stm32f411_gpio_signature/result.json)
  - [stm32g431](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_stm32g431cbu6_stm32g431_gpio_signature/result.json)
  - [stm32h750](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_stm32h750vbt6_stm32h750_wiring_verify/result.json)
  - [stm32f103 ST-Link](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-36-49_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)
- run set `2026-03-20_10-37-43`
  - [esp32c6](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_esp32c6_devkit_esp32c6_gpio_signature_with_meter/result.json)
  - [rp2040](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_rp2040_pico_rp2040_gpio_signature/result.json)
  - [stm32f411](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_stm32f411ceu6_stm32f411_gpio_signature/result.json)
  - [stm32g431](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_stm32g431cbu6_stm32g431_gpio_signature/result.json)
  - [stm32h750](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_stm32h750vbt6_stm32h750_wiring_verify/result.json)
  - [stm32f103 ST-Link](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-37-43_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)
- run set `2026-03-20_10-38-37`
  - [esp32c6](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_esp32c6_devkit_esp32c6_gpio_signature_with_meter/result.json)
  - [rp2040](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_rp2040_pico_rp2040_gpio_signature/result.json)
  - [stm32f411](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_stm32f411ceu6_stm32f411_gpio_signature/result.json)
  - [stm32g431](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_stm32g431cbu6_stm32g431_gpio_signature/result.json)
  - [stm32h750](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_stm32h750vbt6_stm32h750_wiring_verify/result.json)
  - [stm32f103 ST-Link](/nvme1t/work/codex/ai-embedded-lab/runs/2026-03-20_10-38-37_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink/result.json)

## Conclusion

The current claim is now supported by live evidence:

- the six-test default baseline can run in parallel
- the repaired ST-Link path now survives repeated participation in that parallel
  baseline
- the schema/default-verification execution changes are standing on repeatable
  bench evidence, not just unit tests or a single lucky run

Within the scope of this closeout, the baseline should be treated as stable.

## Why Closeout Was Required Here

The risk here was stopping too early after the code fix and one green run.

That would have missed the actual delivery requirement:

- identify the real failure boundary
- prove the repaired path under repetition
- capture the debug method for reuse

This closeout exists to prevent "commit done" from being mistaken for "pattern
validated".
