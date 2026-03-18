# Instrument Action Model Examples v0.1

## Status

Draft

## Related Documents

- [instrument_action_model_v0_1.md](instrument_action_model_v0_1.md) — model spec
- [instrument_action_implementation_plan_v0_1.md](instrument_action_implementation_plan_v0_1.md) — implementation plan

---

## Purpose

This document provides concrete workflow examples for the Instrument Action Model v0.1.

These examples are intended to test whether the abstraction is natural for real AEL usage.

The key question is:

> Can an AI agent understand and use this model easily in real hardware workflows?

If the model feels natural in these examples, it is likely on the right track.

---

## Example 1: STM32 + ST-Link

### Scenario

A single STM32 board is attached to a single ST-Link.

This is a simple, narrow-function workflow.

### Devices

```yaml
devices:
  - name: stm32f411_board_1
    role: dut
    attached_instruments:
      - stlink_1

  - name: stlink_1
    role: instrument
    driver: stlink
    connection:
      usb_serial: auto
    supports:
      - flash
      - reset
      - debug_halt
      - debug_read_memory
    attached_to:
      - stm32f411_board_1
```

### Typical AI task

- flash firmware
- reset DUT
- optionally halt and inspect memory

### Example calls

Flash:

```yaml
run_action:
  dut: stm32f411_board_1
  action: flash
  request:
    firmware: build/app.elf
    format: elf
    verify: true
    reset_after: true
```

Reset:

```yaml
run_action:
  dut: stm32f411_board_1
  action: reset
  request:
    mode: normal
```

Debug read memory:

```yaml
run_action:
  dut: stm32f411_board_1
  action: debug_read_memory
  request:
    address: 0x20000000
    length: 64
```

### Why this example matters

This confirms that a specialized, mostly single-purpose instrument fits naturally into the model.

---

## Example 2: STM32 + ST-Link + USB-UART

### Scenario

One DUT uses two instruments:

- ST-Link for flash/reset/debug
- USB-UART for serial observation

### Devices

```yaml
devices:
  - name: stm32f103_bluepill_1
    role: dut
    attached_instruments:
      - stlink_1
      - usb_uart_1

  - name: stlink_1
    role: instrument
    driver: stlink
    connection:
      usb_serial: auto
    supports:
      - flash
      - reset
      - debug_halt
      - debug_read_memory
    attached_to:
      - stm32f103_bluepill_1

  - name: usb_uart_1
    role: instrument
    driver: usb_uart_bridge
    connection:
      serial_port: /dev/ttyUSB0
    supports:
      - uart_read
      - uart_wait_for
    attached_to:
      - stm32f103_bluepill_1
```

### Typical AI task

- flash firmware using ST-Link
- reset DUT
- wait for UART output `"Hello STM32"`
- conclude PASS/FAIL

### Example calls

Flash:

```yaml
run_action:
  dut: stm32f103_bluepill_1
  action: flash
  request:
    firmware: build/hello.elf
```

Wait for banner:

```yaml
run_action:
  dut: stm32f103_bluepill_1
  action: uart_wait_for
  request:
    baud: 115200
    pattern: "Hello STM32"
    timeout_s: 3.0
```

### Why this example matters

This confirms that one DUT can naturally use multiple attached instruments, each chosen by action.

---

## Example 3: STM32 + ESP JTAG Box

### Scenario

One ESP-based instrument acts as a combined flash/reset/measurement tool.

This is an important multi-function instrument case.

### Devices

```yaml
devices:
  - name: stm32f103_target_1
    role: dut
    attached_instruments:
      - esp_jtag_1

  - name: esp_jtag_1
    role: instrument
    driver: esp_remote_jtag
    connection:
      host: 192.168.1.50
      port: 5555
    supports:
      - flash
      - reset
      - gpio_measure
      - voltage_read
      - signal_capture
    attached_to:
      - stm32f103_target_1
```

### Typical AI task

- flash target
- reset target
- verify GPIO output on a measurement channel
- read VCC
- produce a verification summary

### Example calls

Flash:

```yaml
run_action:
  dut: stm32f103_target_1
  action: flash
  request:
    firmware: build/gpio_test.elf
```

Measure frequency:

```yaml
run_action:
  dut: stm32f103_target_1
  action: gpio_measure
  request:
    channel: ch1
    mode: frequency
    duration_s: 0.5
```

Read voltage:

```yaml
run_action:
  dut: stm32f103_target_1
  action: voltage_read
  request:
    channel: vcc
```

### Why this example matters

This confirms that a multi-function instrument should remain one instrument with many actions, not be artificially split into multiple pseudo-devices.

---

## Example 4: One DUT, Three Instruments

### Scenario

A single DUT is served by three instruments:

- ST-Link for flash/reset/debug
- USB-UART for serial output
- ESP JTAG for GPIO and voltage measurement

### Devices

```yaml
devices:
  - name: stm32f411_board_2
    role: dut
    attached_instruments:
      - stlink_1
      - usb_uart_1
      - esp_jtag_1

  - name: stlink_1
    role: instrument
    driver: stlink
    connection:
      usb_serial: auto
    supports:
      - flash
      - reset
      - debug_halt
      - debug_read_memory
    attached_to:
      - stm32f411_board_2

  - name: usb_uart_1
    role: instrument
    driver: usb_uart_bridge
    connection:
      serial_port: /dev/ttyUSB0
    supports:
      - uart_read
      - uart_wait_for
    attached_to:
      - stm32f411_board_2

  - name: esp_jtag_1
    role: instrument
    driver: esp_remote_jtag
    connection:
      host: 192.168.1.50
      port: 5555
    supports:
      - gpio_measure
      - voltage_read
      - signal_capture
    attached_to:
      - stm32f411_board_2
```

### Typical AI task

- flash firmware via ST-Link
- reset DUT
- wait for UART banner via USB-UART
- verify GPIO signature via ESP JTAG
- combine all evidence into a PASS/FAIL judgment

### Example calls

Flash:

```yaml
run_action:
  dut: stm32f411_board_2
  action: flash
  request:
    firmware: build/test.elf
```

Wait for UART:

```yaml
run_action:
  dut: stm32f411_board_2
  action: uart_wait_for
  request:
    baud: 115200
    pattern: "BOOT OK"
    timeout_s: 5.0
```

Measure signature:

```yaml
run_action:
  dut: stm32f411_board_2
  action: gpio_measure
  request:
    channel: ch1
    mode: signature
    duration_s: 1.0
```

### Why this example matters

This confirms that the model supports evidence collection across multiple instruments without exposing unnecessary internal complexity to the AI.

---

## Example 5: Same Hardware Type, Different Role by Workflow

### Scenario

An ESP32 board type appears in two different workflows.

In workflow A, it is a DUT.
In workflow B, it is an instrument/helper board.

This is a role-switching example.

### Workflow A: ESP32 board as DUT

```yaml
devices:
  - name: esp32s3_board_a
    role: dut
    attached_instruments:
      - usb_uart_1

  - name: usb_uart_1
    role: instrument
    driver: usb_uart_bridge
    connection:
      serial_port: /dev/ttyUSB0
    supports:
      - uart_read
      - uart_wait_for
    attached_to:
      - esp32s3_board_a
```

Typical action:

```yaml
run_action:
  dut: esp32s3_board_a
  action: uart_wait_for
  request:
    baud: 115200
    pattern: "READY"
    timeout_s: 5.0
```

### Workflow B: ESP32 board as instrument

```yaml
devices:
  - name: helper_esp32s3_board_a
    role: instrument
    driver: esp_helper
    connection:
      serial_port: /dev/ttyUSB1
    supports:
      - uart_read
      - gpio_measure
      - signal_generate
```

Typical action:

```yaml
run_action:
  instrument: helper_esp32s3_board_a
  action: signal_generate
  request:
    channel: ch0
    pattern: square_wave
    frequency_hz: 1000
```

### Why this example matters

This confirms that DUT/instrument is a workflow role, not an intrinsic hardware identity.

The model remains stable without requiring a device to have one fixed role across all contexts.

---

## Example 6: Explicit Instrument Selection

### Scenario

A DUT has two compatible instruments for the same action.
The AI or workflow explicitly chooses one.

### Devices

```yaml
devices:
  - name: stm32f103_target_2
    role: dut
    attached_instruments:
      - stlink_1
      - esp_jtag_1

  - name: stlink_1
    role: instrument
    driver: stlink
    connection:
      usb_serial: auto
    supports:
      - flash
      - reset
    attached_to:
      - stm32f103_target_2

  - name: esp_jtag_1
    role: instrument
    driver: esp_remote_jtag
    connection:
      host: 192.168.1.50
      port: 5555
    supports:
      - flash
      - reset
      - gpio_measure
    attached_to:
      - stm32f103_target_2
```

### Explicit selection example

```yaml
run_action:
  instrument: esp_jtag_1
  action: flash
  request:
    firmware: build/app.elf
```

### Why this example matters

This confirms that the model supports both:

- DUT-oriented automatic selection
- explicit instrument-oriented control

This is useful for debugging, benchmarking, and tool preference control.

---

## Example 7: Representative Result Shapes

### Successful UART wait

```yaml
ok: true
action: uart_wait_for
instrument: usb_uart_1
dut: stm32f103_bluepill_1
summary: Pattern matched on UART output
data:
  pattern: "Hello STM32"
  matched: true
  elapsed_s: 1.24
  capture_excerpt: "Booting...\nHello STM32\n"
logs:
  - UART opened at 115200
  - Pattern matched
```

### Failed GPIO measurement

```yaml
ok: false
action: gpio_measure
instrument: esp_jtag_1
dut: stm32f411_board_2
error_code: measurement_failed
message: No valid toggle detected on channel ch1
retryable: true
logs:
  - Channel opened
  - Captured low-level noise
  - No stable periodic waveform found
```

### Failed flash due to unsupported action

```yaml
ok: false
action: flash
instrument: usb_uart_1
dut: stm32f103_bluepill_1
error_code: not_supported
message: Instrument usb_uart_1 does not support action flash
retryable: false
logs: []
```

---

## Example 8: Why These Examples Exist

These examples are meant to pressure-test the abstraction against real AEL needs.

The model should feel natural in all of the following situations:

- one DUT, one specialized instrument
- one DUT, multiple specialized instruments
- one DUT, one multi-function instrument
- one DUT, mixed instrument set
- same hardware type in different roles
- automatic selection and explicit selection
- success and failure paths

If the abstraction handles these examples cleanly, then it is likely a good foundation for implementation.

---

## Summary

These examples support the following conclusions:

- an instrument should remain one instrument even if it supports many actions
- a DUT may naturally have multiple attached instruments
- AI should primarily think in terms of actions, not driver internals
- role is contextual and workflow-specific
- simple config + simple dispatch + structured results are enough for a strong v0.1
