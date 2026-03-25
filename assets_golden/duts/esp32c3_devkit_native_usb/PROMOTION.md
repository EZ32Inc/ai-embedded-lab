# ESP32-C3 DevKit Native USB — Golden Promotion

**Date:** 2026-03-25
**Board ID:** `esp32c3_devkit_native_usb`
**Run ID:** `2026-03-25_12-05-37_esp32c3_devkit_native_usb_esp32c3_suite`

## Result

10/10 tests PASS

```
AEL_SUITE_C3 DONE passed=10 failed=0
```

## Test Coverage

| # | Tag | Description |
|---|-----|-------------|
| 1 | AEL_TEMP | Internal temperature sensor |
| 2 | AEL_NVS | NVS write/read |
| 3 | AEL_WIFI | 2.4 GHz passive scan |
| 4 | AEL_BLE | NimBLE passive scan |
| 5 | AEL_SLEEP | Light sleep + timer wakeup |
| 6 | AEL_PWM | LEDC timer config |
| 7 | AEL_INTR | GPIO edge interrupt loopback |
| 8 | AEL_UART | UART1 TX→RX loopback |
| 9 | AEL_ADC | ADC1 CH1 GPIO-driven loopback |
| 10 | AEL_SPI | SPI2 MOSI↔MISO loopback |

## Wiring (4 jumpers)

| Wire | From | To | Purpose |
|------|------|----|---------|
| 1 | GPIO4 | GPIO5 | GPIO interrupt |
| 2 | GPIO6 | GPIO7 | UART1 TX↔RX |
| 3 | GPIO2 | GPIO1 | ADC drive→sample |
| 4 | GPIO10 | GPIO3 | SPI MOSI↔MISO |

SPI CLK=GPIO21, CS=GPIO20 (freed because console uses USB CDC, not UART0).

## Hardware Notes

- USB type: Native USB Serial/JTAG (VID=0x303a:0x1001, Class B — no CH341)
- Console: `CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y` → /dev/ttyACM0
- No `reset_strategy` needed (native USB does not trigger download mode on port open)
- No PCNT test: ESP32-C3 has no PCNT peripheral (`SOC_PCNT_SUPPORTED` not defined)
- No I2C test: single I2C controller insufficient for master+slave loopback
