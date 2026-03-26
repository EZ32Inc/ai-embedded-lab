# ESP32-S3 DevKit Rule-B Suite 完成报告

**日期：** 2026-03-26
**作者：** Claude (AI) + ali
**主要 Commit：** *(pending commit)*

---

## 1. 工作概述

本次工作为 ESP32-S3 DevKit（双 USB 板）建立完整的 Rule-B 测试架构：14 个独立 IDF 程序（hello + 12 项功能测试 + test_full_suite），涵盖全部 13 个测试项，最终结果 **13/13 PASS**。

ESP32-S3 是 Xtensa LX7 双核处理器，与 RISC-V 系列（C3/C5/C6）在 USB 枚举和 I2C 控制器能力上均有所不同，部分设计决策与 RISC-V 板有显著差异。

---

## 2. 测试套件结构

### 2.1 架构分层

```
Stage 0  ─ hello              (bare-board smoke，无需接线)
Stage 1  ─ nvs / temp / wifi / ble / sleep / pwm   (无需外部跳线)
Stage 2  ─ gpio_intr / pcnt / uart / adc / spi / i2c  (需要跳线)
Rule D   ─ test_full_suite    (13 个子测试合并为一个固件，convenience layer)
```

### 2.2 测试清单

| 测试名 | Stage | 作用 | 设计要点 |
|--------|-------|------|----------|
| `hello` | 0 | 最小烟测：验证 USB CDC 枚举、IDF 启动、printf | 无依赖，验证 UART0（CH341）输出 |
| `test_nvs` | 1 | NVS Flash 读写校验 | `ael_common_init()` 初始化 nvs_flash |
| `test_temp` | 1 | 内部温度传感器读取，5–90°C 校验 | ESP32-S3 内置温度传感器 |
| `test_wifi` | 1 | Wi-Fi 2.4GHz 被动扫描，ap_count ≥ 1 | S3 仅支持 2.4GHz（无 5GHz），无需 set_band_mode |
| `test_ble` | 1 | BLE 被动扫描 3 秒，advertisers ≥ 1 | NimBLE passive scan，测后调用 stop/deinit |
| `test_sleep` | 1 | Light sleep 1 秒 + 定时器唤醒 | 验证低功耗路径 |
| `test_pwm` | 1 | LEDC 1 kHz / 50% duty on GPIO48，配置成功即 PASS | GPIO48 为 S3 安全 PWM 输出口 |
| `test_gpio_intr` | 2 | GPIO4→GPIO5 20 次上升沿中断计数 | INTR 必须在 PCNT 之前（共享 GPIO4/5） |
| `test_pcnt` | 2 | GPIO4 驱动 100 脉冲，GPIO5 PCNT 计数校验 = 100 | 依赖 `gpio_reset_pin(GPIO5)` 在 INTR 后释放 |
| `test_uart` | 2 | UART1 loopback GPIO6→GPIO7，发 "AEL_UART_PING" 收回校验 | UART1（非 UART0 console） |
| `test_adc` | 2 | GPIO2 drive HIGH/LOW → GPIO1 (ADC1_CH0) 读值，hi>2000/lo<500 | GPIO2 为普通 IO，无 LP-IO 限制（S3 优势） |
| `test_spi` | 2 | SPI2 MOSI=GPIO10↔MISO=GPIO11 loopback，8 字节比较 | CLK=GPIO12, CS=GPIO13 |
| `test_i2c` | 2 | HW I2C0 master (GPIO8/9) + HW I2C1 V2 slave (GPIO15/16) | **关键设计决策，见第 3 节** |
| `test_full_suite` | Rule D | 以上 13 个子测试顺序执行 | GPIO5 在 INTR 后 `gpio_reset_pin` 释放供 PCNT 使用 |

### 2.3 接线要求（Stage 2 及 full_suite）

| 跳线 | 用途 |
|------|------|
| GPIO4 ↔ GPIO5 | GPIO interrupt drive / PCNT input（共用） |
| GPIO6 ↔ GPIO7 | UART1 TX → RX loopback |
| GPIO2 → GPIO1 | ADC drive → ADC1_CH0 |
| GPIO10 ↔ GPIO11 | SPI2 MOSI ↔ MISO loopback |
| GPIO8 ↔ GPIO15 | I2C SDA：master (HW I2C0) ↔ slave (HW I2C1) |
| GPIO9 ↔ GPIO16 | I2C SCL：master (HW I2C0) ↔ slave (HW I2C1) |

### 2.4 板卡 USB 配置

| 接口 | 设备 | 用途 |
|------|------|------|
| CH341 UART bridge | `/dev/ttyACM2`（1a86 USB Single Serial, ID=5A7B163835） | Console 输出（UART0），也是烧录及 observe port |
| Native USB Serial/JTAG | `/dev/ttyACM1`（Espressif, MAC=80:B5:4E:C3:9C:7C） | 未使用（S3 console 走 UART0/CH341） |

ESP32-S3 为 Class A 双 USB 板。烧录和 observe 均走 CH341 bridge（`/dev/ttyACM2`），native USB 不参与测试流程。

---

## 3. 关键设计决策

### 3.1 I2C：两个 HP I2C 控制器，无需 bit-bang

ESP32-S3 有两个 HP I2C 控制器（port 0 和 port 1），两者均支持 IDF V2 slave driver（具备 SCL stretch 硬件支持）。

**解决方案**：HW I2C0 作为 master（GPIO8/9），HW I2C1 作为 V2 slave（GPIO15/16）——无需 bit-bang。

这是 S3 相对于 C5/C6 的显著优势。C5/C6 只有一个 HP I2C（另一个为 LP I2C，不支持 V2 slave），必须用 bit-bang master（CE `87240d79`）。S3 的两个 HP I2C 都满足要求，可直接使用双硬件控制器方案。

### 3.2 ADC：GPIO2 无 LP-IO 限制

ESP32-S3 的 GPIO 不区分 LP-IO 和 HP-IO（不同于 C3/C5/C6），GPIO2 可正常输出 HIGH，直接驱动 GPIO1（ADC1_CH0）。无需特殊处理（C3 的 CE `f5aa5241` 在 S3 上不适用）。

### 3.3 Wi-Fi 仅 2.4GHz

ESP32-S3 只支持 Wi-Fi 2.4GHz（不支持 5GHz）。无需调用 `esp_wifi_set_band_mode()`，test_wifi 直接使用默认配置扫描即可通过。此点与 C6（双频，需显式开启）不同。

### 3.4 boot_signatures 与 Xtensa 平台

ESP32-S3 是 Xtensa LX7，理论上 ROM boot 与 RISC-V 不同，但实测同样出现 4 个 IDF boot pattern 触发 false crash_detected。设置 `"boot_signatures": ["rst:0x"]` 解决（与 RISC-V 系列相同，CE `64b74cc2` 适用于 S3）。

### 3.5 端口识别修正

初始 board config 写 `/dev/ttyACM0`（未经硬件验证）。实际挂载后：
- `/dev/ttyACM1` = Espressif native USB JTAG
- `/dev/ttyACM2` = QinHeng CH341 bridge

修正 `configs/boards/esp32s3_devkit_dual_usb.yaml` 及所有 14 个测试计划 JSON 中的 port 为 `/dev/ttyACM2`。

---

## 4. 遇到的问题与解决过程

### 问题一：flash 失败（stage=flash, /dev/ttyACM0 不存在）

**现象**：首次运行 `ael run --test hello.json` 报 flash 失败。

**根本原因**：board config 预设 `/dev/ttyACM0`，但实际系统中 S3 的 CH341 bridge 枚举为 `/dev/ttyACM2`（与 C3 同时连接时端口号偏移）。

**解决方案**：用 `udevadm info` 识别两个 ACM 端口的 vendor/serial，确认 CH341 (1a86) = `/dev/ttyACM2`，更新 board config 及所有测试计划。

---

## 5. 最终测试结果

### 独立测试（Truth Layer）：13/13 PASS

| 测试 | 结果 | Run ID |
|------|------|--------|
| hello | PASS | 2026-03-26_09-57-30 |
| test_nvs | PASS | 2026-03-26_10-00-16 |
| test_temp | PASS | 2026-03-26_10-01-01 |
| test_wifi | PASS | 2026-03-26_10-01-46 |
| test_ble | PASS | 2026-03-26_10-02-48 |
| test_sleep | PASS | 2026-03-26_10-03-45 |
| test_pwm | PASS | 2026-03-26_10-04-30 |
| test_gpio_intr | PASS | 2026-03-26_10-05-24 |
| test_pcnt | PASS | 2026-03-26_10-08-33 |
| test_uart | PASS | 2026-03-26_10-09-20 |
| test_adc | PASS | 2026-03-26_10-10-08 |
| test_spi | PASS | 2026-03-26_10-10-55 |
| test_i2c | PASS | 2026-03-26_10-11-42 |

### Full Suite（Convenience Layer）：13/13 PASS

```
run_id: 2026-03-26_10-12-34_esp32s3_devkit_dual_usb_test_full_suite
result: pass
```

---

## 6. 经验与技能，CE 写入情况

### 写入 CE 的条目

| CE ID | scope | 内容摘要 |
|-------|-------|----------|
| `d6c40a99` | board_family | ESP32-S3 DevKit Rule-B suite 13/13 PASS 完整记录 |

### 复用的已有 CE Pattern

| CE ID | 内容 | 本次应用 |
|-------|------|----------|
| `64b74cc2` | RISC-V ESP32 / Xtensa ESP32 observe_uart boot_signatures fix | S3 同样需要 `boot_signatures: ["rst:0x"]` |
| `7daa8c80` | ESP32 USB 接口分类（Class A dual / Class B native-only） | 确认 S3 为 Class A，flash+observe = CH341 |
| `933fc74a` | Minimal-Instrument Board Bring-up Pattern | 整体 staged bring-up 流程 |

### 关键教训

1. **S3 双 HP I2C 消除 bit-bang 需求**：C5/C6 只有一个 HP I2C，另一个是 LP I2C（不支持 V2 slave），必须用 bit-bang master（CE `87240d79`）。S3 两个控制器均为 HP I2C，可直接双硬件方案——规划 I2C loopback 时须先确认目标 SoC 的 I2C 控制器类型。

2. **boot_signatures fix 适用范围扩展至 Xtensa**：CE `64b74cc2` 原本记录为 RISC-V ESP32 fix，但 S3（Xtensa LX7）也同样出现 4 次 boot pattern 触发 false crash_detected，同样需要 `boot_signatures: ["rst:0x"]`。该 pattern 实际适用于所有现代 ESP32（含 S3）。

3. **S3 无 LP-IO ADC 限制**：C3/C5/C6 存在 LP-IO 无法在 ADC 活跃时输出 HIGH 的限制（CE `f5aa5241`），S3 没有此问题，GPIO2 可直接驱动 ADC 输入。

---

## 7. 文件变更清单

| 文件/目录 | 变更类型 | 说明 |
|-----------|----------|------|
| `firmware/targets/esp32s3_devkit/` | 新增 | 14 个独立测试固件 + common 组件 |
| `tests/plans/esp32s3_devkit/` | 新增 | 14 个测试计划 JSON（port=/dev/ttyACM2） |
| `packs/esp32s3_devkit_full.json` | 新增 | 14 测试 pack |
| `packs/esp32s3_full_suite.json` | 更新 | 指向 Rule-B 测试计划 |
| `configs/boards/esp32s3_devkit_dual_usb.yaml` | 更新 | port 修正为 /dev/ttyACM2，build.project_dir 修正 |

---

## 8. Summary

ESP32-S3 DevKit Rule-B suite 在 2026-03-26 完成全部 13/13 PASS。

**主要贡献**：

1. **HW I2C0 master + HW I2C1 V2 slave（无 bit-bang）**：充分利用 S3 双 HP I2C 控制器，比 C5/C6 的 bit-bang 方案更简洁、更可靠。这是 S3 相对于 RISC-V 系列的架构优势，应在未来 S3 衍生板的规划中优先使用。

2. **boot_signatures fix 普适性验证**：CE `64b74cc2` 在 S3（Xtensa）上验证有效，证明该 fix 不限于 RISC-V，适用于所有现代 ESP32。

3. **端口识别标准化**：验证了使用 `udevadm info` + Vendor ID 识别 CH341 vs native USB JTAG 的方法，为后续新板挂载提供可重复流程。

## Civilization Engine Usage Audit

查询了什么：`HIGH_PRIORITY`、`esp32s3`、`boot_signatures`、`i2c`
命中了什么：`64b74cc2`（boot_signatures fix）、`7daa8c80`（USB 分类）、`87240d79`（I2C bit-bang，参考但未采用）、`933fc74a`（bring-up pattern）
是否复用：是（`64b74cc2` boot_signatures、`7daa8c80` USB 分类、`933fc74a` staged flow）
新增记录：`d6c40a99`（S3 board_family 完成记录）
升级资产：`64b74cc2` 适用范围从"RISC-V"扩展为"所有现代 ESP32"（含 Xtensa S3）
