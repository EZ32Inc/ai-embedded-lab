# Promotion Record

source_draft:       esp32s3_devkit_dual_usb
source_namespace:   branch
promoted_to:        esp32s3_devkit_dual_usb
promoted_at:        2026-03-25T00:00:00Z

## Evidence at Promotion

  lifecycle_stage:    merged_to_main
  compile_validation: passed
  bench_validation:   passed — 12/12 PASS on real hardware (2026-03-25)

## Verification Summary

  Board:    ESP32-S3 DevKit Dual USB
  Firmware: firmware/targets/esp32s3_suite
  Pack:     packs/esp32s3_full_suite.json
  Result:   12/12 PASS

  Test results:
    AEL_TEMP  celsius=28.2          PASS
    AEL_NVS   wrote=0xAE3A0001      PASS
    AEL_WIFI  ap_2g=15              PASS  (2.4GHz only — S3 has no 5GHz)
    AEL_BLE   advertisers=49        PASS
    AEL_SLEEP wakeup_cause=4        PASS
    AEL_PWM   gpio=GPIO48           PASS
    AEL_INTR  triggered=20/20       PASS
    AEL_PCNT  counted=100/100       PASS
    AEL_UART  sent=13 recv=13       PASS
    AEL_ADC   hi=4095 lo=0          PASS
    AEL_SPI   tx_rx_match=1         PASS
    AEL_I2C   rx_len=8 match=1      PASS

## Key Design Decisions

  - Flash+console: CH341 UART bridge /dev/ttyACM0 (RTS/DTR auto-reset)
  - Native USB JTAG (/dev/ttyACM1): unused in suite
  - I2C: HW I2C0 master (GPIO8/9) + HW I2C1 slave V2 (GPIO15/16)
    S3 has two I2C ports — no bit-bang required (unlike C5)
  - WiFi: 2.4GHz passive scan only — no esp_wifi_set_band_mode()
  - PCNT/INTR share GPIO4/5; INTR runs before PCNT (same as C5 pattern)
  - CE pattern: 0ee28e73

## Wiring (6 jumpers)

  GPIO4  ↔ GPIO5   PCNT + GPIO interrupt
  GPIO6  ↔ GPIO7   UART1 TX→RX loopback
  GPIO2  →  GPIO1  GPIO output → ADC1_CH0
  GPIO11 ↔ GPIO13  SPI2 MOSI↔MISO (CLK=GPIO12, CS=GPIO10)
  GPIO8  ↔ GPIO15  I2C0 SDA master ↔ I2C1 SDA slave
  GPIO9  ↔ GPIO16  I2C0 SCL master ↔ I2C1 SCL slave
  GPIO48 — PWM (no wire)
