# Default Verification Live Validation Follow-up

Date: 2026-03-20

## Scope

This note records the first real post-schema validation sweep after the test-plan schema, schema advisory, baseline review, and readiness surfaces were wired through:

- inventory / explain
- verify-default state / review
- ael status
- nightly summary / review pack / nightly report

The goal of this round was not more schema plumbing. The goal was to answer a practical question:

Is the system still stable when exercised through real default-verification runs?

## What Was Run

### Representative single-run checks

Three representative default-verification single-run configs were exercised:

1. Mailbox / ST-Link path
   - board: `stm32f103_gpio_stlink`
   - test: `tests/plans/stm32f103_gpio_no_external_capture_stlink.json`

2. Meter path
   - board: `esp32c6_devkit`
   - test: `tests/plans/esp32c6_gpio_signature_with_meter.json`

3. Banner / meter-backed UART path
   - board: `esp32c6_devkit`
   - test: `tests/plans/esp32c6_uart_banner.json`

### Full default baseline

The current repo-native baseline was also run directly:

```bash
PYTHONPATH=. python3 -m ael verify-default run
```

### Baseline minus known meter issue

Because `esp32c6_gpio_signature_with_meter` remained a known single-point runtime issue, a temporary baseline-minus-meter config was also run to verify the rest of the baseline independently.

## Main Outcomes

### 1. Schema rollout did not destabilize the project

This is the main conclusion from the round.

We observed:

- one full default baseline run at `6/6 PASS`
- one repeat full default baseline run at `5/6`, where the only failing step was the already-known meter path
- one baseline-minus-meter run at `5/5 PASS`

That is strong evidence that the schema work did not introduce broad runtime instability.

### 2. Baseline review signals continued to match reality

During successful baseline runs, the schema/readiness signals remained internally consistent:

- structured / legacy counts were populated correctly
- test kind distribution was correct
- supported instrument advisory status remained `declared_supported`
- warning summary stayed empty when runs passed cleanly

This matters because the schema work was not only about plan metadata. It also introduced new review surfaces and readiness signals. Those surfaces continued to describe the real run state correctly.

### 3. Meter remains a known single-point issue

The `esp32c6_gpio_signature_with_meter` path still showed runtime instability across repeats.

This should be treated as a specific meter-path issue, not as evidence of general schema or baseline instability.

Current recommendation:

- keep it visible
- do not treat it as blocking overall schema closeout
- triage it separately as a focused runtime issue

### 4. Banner moved from setup failure to runtime flake

The `esp32c6_uart_banner` path evolved across runs:

- earlier failure mode: `flash`-stage failure when hardware was not yet powered correctly
- later failure mode: `observe_uart` failure with zero UART bytes captured
- later repeat: successful pass

This means the path is now in a much healthier state than before. It is no longer failing at setup/flash. It is now better characterized as a flaky runtime/UART-observe path.

## Detailed Banner Finding

The most useful debugging result from this round was the banner comparison.

The failing run:

- run: `runs/2026-03-20_05-17-06_esp32c6_devkit_esp32c6_uart_banner`
- `flash.json`: success, port `/dev/ttyACM0`
- `uart_observe.json`: `bytes=0`, `lines=0`
- failure: missing expected UART pattern `AEL_READY ESP32C6 UART`

The succeeding runs:

- run: `runs/2026-03-19_21-50-29_esp32c6_devkit_esp32c6_uart_banner`
- run: `runs/2026-03-20_05-33-12_esp32c6_devkit_esp32c6_uart_banner`

The successful raw UART capture contained repeated:

```text
AEL_READY ESP32C6 UART
```

The failure run contained zero lines, not a wrong banner and not an obvious crash log.

That suggests:

- the banner firmware is capable of working as-is
- the test plan expectation is correct
- the failure is more likely in runtime timing, serial acquisition timing, or environment state than in the schema or the banner string itself

## Important Technical Observation

During triage, one implementation gap became visible:

- `bench_setup.serial_console.port` is present in the effective plan metadata as `auto_usb_serial_jtag`
- but the generated `check_uart` step still carried `observe_uart_cfg.port = null`
- the UART step then relied on `flash.json.port` fallback, which became `/dev/ttyACM0`

This did not block successful runs, because the fallback path is often enough.

But it is a real implementation detail worth keeping in mind for future UART-flake cleanup:

- the UART observe step is not yet explicitly wired from the serial-console declaration
- it currently depends on flash-stage port propagation when `observe_uart.port` is unset

This is not the root cause of every banner failure, but it is a good candidate area for future hardening.

## Representative Run References

### Mailbox representative pass

- `runs/2026-03-20_05-02-08_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink`

### Meter representative fail

- `runs/2026-03-20_05-02-11_esp32c6_devkit_esp32c6_gpio_signature_with_meter`

### Banner representative fail then pass

- `runs/2026-03-20_05-17-06_esp32c6_devkit_esp32c6_uart_banner`
- `runs/2026-03-20_05-33-12_esp32c6_devkit_esp32c6_uart_banner`

### Full baseline pass

- meter + legacy + mailbox mixed baseline passed earlier in this round

### Baseline-minus-meter pass

- `runs/2026-03-20_05-35-09_rp2040_pico_rp2040_gpio_signature`
- `runs/2026-03-20_05-35-09_stm32f411ceu6_stm32f411_gpio_signature`
- `runs/2026-03-20_05-35-09_stm32g431cbu6_stm32g431_gpio_signature`
- `runs/2026-03-20_05-35-09_stm32h750vbt6_stm32h750_wiring_verify`
- `runs/2026-03-20_05-35-09_stm32f103_gpio_stlink_stm32f103_gpio_no_external_capture_stlink`

## Decision

The schema program should be considered complete enough to exit the design/plumbing phase.

The project should now operate in a validation/stability phase:

- keep the schema surfaces as-is unless a concrete defect appears
- treat the meter path as a focused runtime issue
- treat banner as a focused flaky UART/runtime issue
- treat the rest of the default baseline as currently healthy

## Recommended Next Steps

1. Keep `esp32c6_gpio_signature_with_meter` as a known issue and triage it separately.
2. Do a focused hardening pass on `esp32c6_uart_banner` UART observation stability.
3. Continue using baseline-minus-meter as a practical health signal if a temporarily green operator baseline is needed.
4. Avoid reopening broad schema work unless future runtime validation exposes a concrete schema-consumer defect.
