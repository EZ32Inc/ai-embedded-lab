# ESP32-S3 Golden GPIO Signature Test (Meter-Based)

This golden test verifies an ESP32-S3 DUT with an external Wi-Fi instrument (`esp32s3_dev_c_meter`) after build/flash/UART checks.

Use CON1 (native USB, typically `/dev/ttyACM*`) for both flashing/reset and UART log observation.

## Wiring

DUT to instrument:
- DUT GPIO4 (X1) -> Instrument GPIO11 (DIN0), expected toggle (~1kHz)
- DUT GPIO5 (X2) -> Instrument GPIO12 (DIN1), expected toggle (~2kHz)
- DUT GPIO6 (X3) -> Instrument GPIO13 (DIN2), expected high
- DUT GPIO7 (X4) -> Instrument GPIO14 (DIN3), expected low
- DUT 3V3 -> Instrument ADC GPIO4 (AD), expected within 3.0V..3.45V
- DUT GND -> Instrument GND

Avoid DUT strapping pins (for example GPIO0) and USB pins.

## Instrument AP

Connect the PC Wi-Fi interface to:
- SSID: `ESP32_GPIO_METER_xxxx`
- Password: `esp32gpiom`
- TCP endpoint: `192.168.4.1:9000`

## Run (AI control plane)

```bash
python3 -m ael run \
  --board esp32s3_devkit \
  --test tests/esp32s3_gpio_signature_with_meter.json \
  --probe configs/esp32jtag.yaml
```

Notes:
- This test disables classic ESP32JTAG preflight with `"preflight": {"enabled": false}`.
- Instrument selftest is disabled by default (`"instrument.run_selftest": false`) because loopback wires are not assumed.
- UART observe uses the same serial port selected for flashing (CON1).
- Artifacts include:
  - `instrument_digital.json`
  - `instrument_voltage.json` (when analog checks are configured)
  - `verify_result.json`
