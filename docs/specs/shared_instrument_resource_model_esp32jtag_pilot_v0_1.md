# Shared Instrument Resource Model ESP32JTAG Pilot v0.1

## Concrete pilot

Pilot instrument:

- `esp32jtag_stm32_golden`
- endpoint `192.168.2.99:4242`

Current bounded execution evidence comes from the STM32 workers in the 4-worker
default suite:

- `stm32f103_golden_gpio_signature`
- `stm32f103_uart_bridge_banner`

These two workers are now correctly separated by DUT identity:

- `dut:stm32f103`
- `dut:stm32f103_uart`

They still serialize on:

- `probe_path:/nvme1t/work/codex/ai-embedded-lab/configs/instrument_instances/esp32jtag_stm32_golden.yaml`

## What is clearly whole-device exclusive

For this pilot, the following operations should be treated as whole-device
exclusive unless proven otherwise:

- SWD attach
- flash/program/load
- reset control
- debug-state control
- global capture/sampling reconfiguration

These operations affect the whole instrument session or the whole target-facing
mode of the instrument.

## What might be shareable in principle

The following could be shareable in principle only if the instrument model were
extended safely:

- passive GPIO/logic capture on disjoint channels
- passive observation on independent input pins

This remains conceptual only. The current baseline does not prove that such
sharing is safe on `esp32jtag_stm32_golden`.

## What the current baseline really proves

The current 4-worker suite proves:

1. false DUT-level collapsing was a real bug and was fixed
2. remaining STM32 serialization is now caused by shared control-instrument
   ownership, not by shared DUT identity
3. the bounded STM32 UART path is healthy as a separate DUT using the same
   control instrument

## What it does not prove

The current baseline does not prove:

- that `esp32jtag_stm32_golden` can safely support concurrent same-capability
  access
- that two capture paths on different channels can coexist safely
- that current whole-device blocking is overly coarse for the active STM32
  workers

## Pilot conclusion

For this pilot, current evidence is sufficient to say:

- the DUT split was necessary and correct
- current whole-device control-instrument blocking is still the correct safe
  runtime behavior

Current evidence is not sufficient to justify relaxing control-instrument
blocking for the active STM32 default-verification paths.

