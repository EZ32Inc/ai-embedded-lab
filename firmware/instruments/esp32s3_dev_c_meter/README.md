# ESP32-S3 DevKitC Meter Instrument

This firmware turns an ESP32-S3 DevKitC into a simple GPIO/ADC meter and digital stim board.

## Wi-Fi SoftAP

- SSID: `ESP32_GPIO_METER_xxxx` (xxxx = last 4 hex of MAC)
- Password: `esp32gpiom`
- TCP port: `9000`
- Default AP IP: `192.168.4.1`

## TCP Commands

Send ASCII commands, one per line. Each command returns one JSON line.

Examples:

```
PING
MEAS DIGITAL PINS=11,12,13,14 DUR_MS=500
MEAS VOLT GPIO=4 AVG=16
STIM DIGITAL GPIO=15 MODE=high
STIM DIGITAL GPIO=15 MODE=toggle DUR_US=100000 FREQ_HZ=1000
STIM DIGITAL GPIO=15 MODE=pulse DUR_US=50 PATTERN=lhl
SELFTEST OUT=15 IN=11 ADC_OUT=16 ADC_IN=4 DUR_MS=200 FREQ_HZ=1000 AVG=16 SETTLE_MS=20
```

## Selftest Wiring

Loopback:

- GPIO15 (output) -> GPIO11 (input)  (digital loopback)
- GPIO16 (output) -> GPIO4 (ADC input)  (ADC loopback)

Command:

`SELFTEST OUT=15 IN=11 ADC_OUT=16 ADC_IN=4 DUR_MS=200 FREQ_HZ=1000 AVG=16 SETTLE_MS=20`

Expected:

- `pass=true` with `digital.pass=true` and `adc.pass=true`
- Digital includes low/high/toggle state and transitions
- ADC includes `v_low` and `v_high` checks

Behavior summary:

- Digital pass requires low/high/toggle state match and toggle transitions > 10.
- ADC pass requires approximately `v_low < 0.30V` and `v_high > 2.60V` (looser thresholds if ADC calibration is unavailable).
- Outputs return to Hi-Z after selftest unless `KEEP=1`.

## Safety

- 3.3V logic only.
- Common ground required.
- Outputs default to Hi-Z on boot and after stim unless KEEP=1.
