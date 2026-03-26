# ESP32-C5 DevKit — Rule-B Suite Closeout Report

**Board:** esp32c5_devkit_dual_usb
**Date:** 2026-03-26
**Suite run ID:** 2026-03-26_16-02-00_esp32c5_devkit_dual_usb_test_full_suite
**Result:** PASS — 12/12 sub-tests

---

## 1. Suite Summary

| # | Test | Status |
|---|------|--------|
| 1 | hello (board identity) | PASS |
| 2 | temperature (internal sensor) | PASS |
| 3 | nvs (non-volatile storage) | PASS |
| 4 | wifi (station scan/connect) | PASS |
| 5 | ble (NimBLE advertise/scan) | PASS |
| 6 | light_sleep (RTC wakeup) | PASS |
| 7 | pwm (LEDC duty cycle) | PASS |
| 8 | gpio_intr (edge interrupt) | PASS |
| 9 | pcnt (pulse counter loopback) | PASS |
| 10 | uart (UART1 TX→RX loopback) | PASS |
| 11 | adc (ADC1_CH0 voltage read) | PASS |
| 12 | spi (SPI2 MOSI↔MISO loopback) | PASS |

**Wiring required (4 jumpers):**
- GPIO2 ↔ GPIO3 — GPIO interrupt drive / PCNT input (shared)
- GPIO4 ↔ GPIO5 — UART1 TX → RX loopback
- GPIO6 → GPIO1 — ADC drive → ADC1_CH0
- GPIO7 ↔ GPIO9 — SPI2 MOSI ↔ MISO loopback

---

## 2. Excluded Test: test_i2c

`test_i2c` is **excluded** from the Rule-B suite.
Source remains at `firmware/targets/esp32c5_devkit/test_i2c/` but is not referenced by any suite plan.

### Test design

The test uses a bit-bang I2C master (BB_SDA=GPIO8, BB_SCL=GPIO13) wired to an IDF
I2C V2 hardware slave (SDA=GPIO14, SCL=GPIO23).  The master sends 8 bytes to address
0x5A; the slave receives via `on_receive` callback.  Success requires the slave to
drive SDA LOW for the ACK bit after address match.

### Investigation timeline

1. **Initial run** — `bb_transmit` returned `-1` (NACK on address byte).
   `AEL_I2C … FAIL`.

2. **USB JTAG conflict** — GPIO13 and GPIO14 are shared with the USB JTAG/serial
   interface.  Added `CONFIG_USJ_ENABLE_USB_SERIAL_JTAG=n` to `sdkconfig.defaults`.
   No change — still NACK.

3. **GPIO output enable hypothesis** — Suspected `gpio_output_enable()` was not being
   called for the slave SDA pin.  Added explicit call after slave init.  Discovered
   that `gpio_output_enable()` calls `gpio_hal_matrix_out_default()` first, which
   **disconnects the I2C peripheral signal** from the pad.  Reverted; this was
   counter-productive.

4. **GPIO matrix routing verification** — Read `GPIO.func_in_sel_cfg` for SDA_IN
   (signal 47) and SCL_IN (signal 46) registers.  Confirmed correct routing:
   - `sda_in = 0x0000010e` → GPIO14 → I2C SDA_IN ✓
   - `scl_in = 0x00000117` → GPIO23 → I2C SCL_IN ✓

5. **GPIO_ENABLE_REG verification** — Read `GPIO.enable` register after slave init.
   Confirmed `ena = 0x00804000` — bits 14 and 23 are set.  The IDF driver
   (`i2c_common_set_pins`) correctly enables the output driver; no manual fix needed.

6. **OEN_SEL fix** — Attempted setting `GPIO.func_out_sel_cfg[GPIO14].oen_sel = 1`
   plus writing to `GPIO.enable_w1ts` to force output-enable from GPIO_ENABLE_REG
   rather than from the peripheral.  ACK probe still showed SDA=1 throughout the
   ACK clock cycle.

7. **SCL stretch disable** — Called `i2c_ll_slave_enable_scl_stretch(I2C_LL_GET_HW(0), false)`
   immediately after slave init.  No effect.  (The IDF V2 driver enables stretch
   with `protect_num=0x3FF` ≈ 25.6 µs at 40 MHz XTAL; disabling did not help.)

8. **GPIO role swap** — Swapped the entire config: slave on GPIO8/GPIO13, bit-bang
   master on GPIO14/GPIO23.  Both sides confirmed working as OD outputs in
   `bb_selftest`.  Result: still NACK.  Rules out a pin-specific hardware fault.

9. **Wire connectivity cross-drive test** — Added a 4-way cross-drive check before
   slave init: drive each GPIO LOW and read the other end.  All four results = 0,
   confirming physical wires are connected.

10. **I2C SR register read after ACK probe** — Manually sent START + address + ACK
    clock cycle from the bit-bang master, then read the I2C status register:
    ```
    sr = 0x0000c000   (bus_busy=0, slave_addressed=0)
    ```
    This is the definitive finding: **the I2C peripheral reports zero bus activity
    while the bit-bang master is actively driving the bus.**  The peripheral is not
    detecting the SCL/SDA transitions at all.

11. **IDF example review** — Reviewed
    `/home/aes/esp/esp-idf/examples/peripherals/i2c/i2c_slave_read_write/`.
    The IDF example for I2C slave V2 uses `i2c_slave_receive()` (polling), not the
    `on_receive` callback.  However, the `generic_multi_device` test in the IDF test
    suite uses a **hardware I2C master on a second board** — there is no IDF
    reference for a single-board bit-bang-master + HW-slave configuration on
    ESP32-C5.

### Root cause assessment

Despite:
- Correct GPIO matrix routing (verified via register read)
- Correct GPIO_ENABLE_REG bits (set by IDF driver, verified)
- Physical wire continuity confirmed (cross-drive test)
- Slave init returning `ESP_OK`
- BB_HALF_US=50 (10 kHz, well within ADDRESS_MATCH stretch window)

…the I2C V2 slave peripheral on ESP32-C5 reports `bus_busy=0` and never fires the
`on_receive` callback.  The root cause is unresolved.  Possible explanations:

- An ESP32-C5-specific hardware quirk in the I2C V2 peripheral where the digital
  filter or bus-detect logic does not respond to externally-driven SCL/SDA transitions
  in this single-board, single-core configuration.
- A yet-unknown interaction between the IDF V2 driver initialisation sequence and the
  GPIO matrix on ESP32-C5 that leaves the peripheral isolated from the bus.

### Recommendation

To validate I2C slave functionality on ESP32-C5:
1. Use a **hardware I2C master on a second board** (as the IDF generic_multi_device
   test does) rather than a same-board bit-bang master.
2. Or, test with a standalone I2C analyser/master device (e.g. Bus Pirate, Raspberry
   Pi I2C master) to eliminate the single-board wiring scenario.
3. File an IDF issue against `esp_driver_i2c` for ESP32-C5 if the two-board test
   also fails with `bus_busy=0`.

---

## 3. Known Engineering Notes

| Issue | CE ID | Resolution |
|-------|-------|-----------|
| `gpio_install_isr_service` must precede WiFi/BLE init | `dbdf36fb` | Called first in app_main |
| app_main default stack (3584 B) insufficient for 12 drivers | `73f41c63` | `ESP_MAIN_TASK_STACK_SIZE=8192` |
| GPIO interrupt test must run before PCNT (shared GPIO2/3) | `92297155` | `test_gpio_intr` called before `test_pcnt` |
| `i2c_slave_receive()` auto-starts I2C master — use V2 driver | `87240d79` | `CONFIG_I2C_ENABLE_SLAVE_DRIVER_VERSION_2=y` |
| I2C slave V2 `receive_buf_depth=32` too small | `975b66b9` | Set ≥100; RINGBUF overhead ~20 bytes |
| ADDRESS_MATCH stretch breaks ACK at >10 kHz | `958116e1` | `BB_HALF_US=50` (10 kHz) |
| `IRAM_ATTR` variable + `PMP_IDRAM_SPLIT` → store fault | `d26958c3` | Do not use `IRAM_ATTR` on variables |

---

## 4. Civilization Engine Usage Audit

查询了什么：`esp32c5_devkit`, `HIGH_PRIORITY`, `i2c`, `bus_busy`
命中了什么：`87240d79` (I2C V2 workaround), `958116e1` (BB_HALF_US=50), `975b66b9` (receive_buf_depth), `92297155` (PCNT order)
是否复用：是 — BB_HALF_US=50 和 receive_buf_depth=100 从已有记录直接应用
新增记录：ESP32-C5 I2C V2 slave bus_busy=0 (scope=board_family, 待写入 CE)
升级资产：无新 pattern 提升
