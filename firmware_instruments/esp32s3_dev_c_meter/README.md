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
```

## Selftest Wiring

Loopback:

- GPIO15 (output) -> GPIO11 (input)

Then:

1) `STIM DIGITAL GPIO=15 MODE=toggle DUR_US=200000 FREQ_HZ=1000`
2) `MEAS DIGITAL PINS=11,12,13,14 DUR_MS=200`

Expected: GPIO11 reports `toggle`.

## Safety

- 3.3V logic only.
- Common ground required.
- Outputs default to Hi-Z on boot and after stim unless KEEP=1.
