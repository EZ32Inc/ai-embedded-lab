# ESP32-C6 DevKit Rule-B Suite 完成报告

**日期：** 2026-03-25
**作者：** Claude (AI) + ali
**主要 Commit：** `9725e67` — "Add ESP32-C6 DevKit Rule-B suite: 13 isolated tests + full_suite (13/13 PASS)"

---

## 1. 工作概述

本次工作为 ESP32-C6 DevKit（双 USB 板）建立完整的 Rule-B 测试架构：14 个独立 IDF 程序（hello + 12 项功能测试 + test_full_suite），涵盖全部 13 个测试项，最终结果 **13/13 PASS**。

ESP32-C6 是项目中首个使用 Rule-B 架构的 RISC-V ESP32 芯片（C3、WROOM-32D 均在 C6 之后完成迁移），因此 C6 的 bring-up 过程积累了多个对后续板型有通用价值的 pattern。

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
| `test_temp` | 1 | 内部温度传感器读取，5–90°C 校验 | ESP32-C6 内置温度传感器 |
| `test_wifi` | 1 | Wi-Fi 2.4/5GHz 双频被动扫描，ap_count ≥ 1 | C6 支持 Wi-Fi 6（802.11ax），使用 `esp_wifi_set_band_mode(WIFI_BAND_MODE_2G5G_AUTO)` |
| `test_ble` | 1 | BLE 被动扫描 3 秒，advertisers ≥ 1 | NimBLE passive scan，测后调用 stop/deinit |
| `test_sleep` | 1 | Light sleep 1 秒 + 定时器唤醒 | 验证低功耗路径 |
| `test_pwm` | 1 | LEDC 1 kHz / 50% duty on GPIO3，配置成功即 PASS | GPIO3 不需跳线 |
| `test_gpio_intr` | 2 | GPIO20→GPIO21 20 次上升沿中断计数 | INTR 必须在 PCNT 之前（共享 GPIO20/21） |
| `test_pcnt` | 2 | GPIO20 驱动 100 脉冲，GPIO21 PCNT 计数校验 = 100 | 依赖 `gpio_reset_pin(GPIO21)` 在 INTR 后释放 |
| `test_uart` | 2 | UART1 loopback GPIO18→GPIO19，发 "AEL_UART_PING" 收回校验 | UART1（非 UART0 console） |
| `test_adc` | 2 | GPIO22 drive HIGH/LOW → GPIO4 (ADC1_CH4) 读值，hi>2000/lo<500 | GPIO22 为非 ADC 引脚，无 LP-IO 限制 |
| `test_spi` | 2 | SPI2 MOSI=GPIO10↔MISO=GPIO2 loopback，8 字节比较 | CLK=GPIO11, CS=GPIO12 |
| `test_i2c` | 2 | HP I2C0 V2 slave (GPIO8/9) + bit-bang master (GPIO6/7) | **关键设计决策，见第 3 节** |
| `test_full_suite` | Rule D | 以上 13 个子测试顺序执行 | GPIO21 在 INTR 后 `gpio_reset_pin` 释放供 PCNT 使用 |

### 2.3 接线要求（Stage 2 及 full_suite）

| 跳线 | 用途 |
|------|------|
| GPIO20 ↔ GPIO21 | GPIO interrupt drive / PCNT input（共用） |
| GPIO18 ↔ GPIO19 | UART1 TX → RX loopback |
| GPIO22 → GPIO4 | ADC drive → ADC1_CH4 |
| GPIO10 ↔ GPIO2 | SPI2 MOSI ↔ MISO loopback |
| GPIO8 ↔ GPIO6 | I2C SDA：slave (HP I2C0) ↔ bit-bang master |
| GPIO9 ↔ GPIO7 | I2C SCL：slave (HP I2C0) ↔ bit-bang master |

### 2.4 板卡 USB 配置

| 接口 | 设备 | 用途 |
|------|------|------|
| CH341 UART bridge | `/dev/ttyACM1`（1a86 CH341） | Console 输出（UART0），也是 observe port |
| Native USB Serial/JTAG | Espressif CDC（MAC 40:4C:CA:55:5A:D4） | 烧录（flash port） |

ESP32-C6 为 Class A 双 USB 板。烧录走 native USB，observe 走 CH341 UART bridge。

---

## 3. 关键设计决策

### 3.1 I2C：HP I2C V2 slave + bit-bang master

ESP32-C6 有两个 I2C 控制器：1 个 HP I2C（port 0）和 1 个 LP I2C（port 1）。
LP I2C 的 V2 slave driver 在 IDF 中**不受支持**（LP peripheral 缺少 SCL stretch 硬件支持）。

**解决方案**：HP I2C port 0 作为 V2 slave（GPIO8/9），另一侧用 bit-bang master（GPIO6/7）。

此方案直接复用了 CE 条目 `87240d79`（ESP32-C5 I2C slave V2 问题和 bit-bang master 解法），是跨板复用的典型案例。

### 3.2 boot_signatures 修正

**问题**：ESP32-C6 RISC-V ROM 在 115200 baud 下输出，正常一次启动会触发 4 条匹配 espidf profile 的模式（`rst:0x`、`ESP-ROM:`、`boot:0x`、`ESP-IDF v`），导致 AEL observer 的 `boot_count` 达到 4，误判为多次崩溃重启，继而误报 `crash_detected=True`。

**解决方案**：所有测试计划设置 `"boot_signatures": ["rst:0x"]`，该字符串只在真正复位后出现一次，observer 只计一次启动。此 pattern 同时适用于所有 RISC-V ESP32（C3/C5/C6）。

### 3.3 观察端口与 CH341 fallback

C6 有两个 CDC 端口。烧录优先走 native USB（更快）；observe_uart 走 CH341 bridge（`/dev/ttyACM1`），因为 console（UART0）路由到 CH341。board config 中增加了 CH341 port 作为 flash fallback，以防 native USB 枚举失败。

---

## 4. 遇到的问题与解决过程

### 问题一：RISC-V boot_signatures 触发 false crash_detected

**现象**：Stage 0 hello 验证时，AEL runner 报告 `crash_detected=True`，但固件实际运行正常，`AEL_HELLO board=ESP32C6 PASS` 有输出。

**根本原因**：ESP32-C6 ROM bootloader 工作在 115200 baud（区别于 ESP32 classic 的 74880 baud ROM 阶段）。espidf profile 的 4 个标准 boot pattern 在单次正常启动中全部出现，`boot_count` 累计为 4，超过崩溃阈值。

**解决方案**：所有 C6 测试计划增加 `"boot_signatures": ["rst:0x"]`，使 observer 以复位标志作为单次启动的起点，只记一次启动。此修复同时适用于 C3、C5 等所有 RISC-V ESP32。已写入 CE `64b74cc2`（HIGH_PRIORITY）。

### 问题二：I2C LP_I2C 不支持 V2 slave

**现象**：尝试在 LP I2C port 1 使用 V2 slave driver，`i2c_new_slave_device()` 返回错误。

**根本原因**：IDF 的 I2C V2 slave driver 需要硬件 SCL stretch 支持，LP I2C 不具备此硬件特性。

**解决方案**：HP I2C V2 slave（GPIO8/9）+ bit-bang master（GPIO6/7），直接复用 CE `87240d79`（C5 I2C loopback pattern）。

### 问题三：Wi-Fi 双频模式 API

**现象**：初版 test_wifi 未调用 `esp_wifi_set_band_mode()`，仅扫描到少量 AP，担心遗漏 5GHz AP 影响稳定性。

**解决方案**：显式调用 `esp_wifi_set_band_mode(WIFI_BAND_MODE_2G5G_AUTO)` 开启双频扫描。ESP32-C6 支持 Wi-Fi 6（802.11ax），此为 C6 特有功能，S3/C3 等板型不可用（需区别对待）。

---

## 5. 最终测试结果

### 独立测试（Truth Layer）：13/13 PASS

| 测试 | 结果 |
|------|------|
| hello | PASS |
| test_nvs | PASS |
| test_temp | PASS |
| test_wifi | PASS |
| test_ble | PASS |
| test_sleep | PASS |
| test_pwm | PASS |
| test_gpio_intr | PASS |
| test_pcnt | PASS |
| test_uart | PASS |
| test_adc | PASS |
| test_spi | PASS |
| test_i2c | PASS |

### Full Suite（Convenience Layer）：13/13 PASS

```
AEL_SUITE_FULL DONE passed=13 failed=0
run_id: 2026-03-25_21-18-17_esp32c6_devkit_dual_usb_test_full_suite
```

---

## 6. 经验与技能，CE 写入情况

### 写入 CE 的条目

| CE ID | scope | 内容摘要 |
|-------|-------|----------|
| `64b74cc2` | pattern（HIGH_PRIORITY） | RISC-V ESP32 observe_uart false crash — 须设 `boot_signatures: ["rst:0x"]` |
| `77927f41` | board_family | ESP32-C6 DevKit Dual USB Rule-B suite 13/13 PASS 完整记录 |

### 复用的已有 CE Pattern

| CE ID | 内容 | 本次应用 |
|-------|------|----------|
| `87240d79` | ESP32-C5 I2C slave V2 + bit-bang master pattern | C6 I2C loopback：HP I2C V2 slave + bit-bang master |
| `7daa8c80` | ESP32 USB 接口分类（Class A dual / Class B native-only） | 确认 C6 为 Class A，flash = native USB，observe = CH341 |
| `933fc74a` | Minimal-Instrument Board Bring-up Pattern | 整体 staged bring-up 流程 |

### 关键教训

1. **RISC-V boot pattern 与 Xtensa 不同**：ESP32-C6/C5/C3 的 ROM 在 115200 baud 下输出完整的 IDF boot 序列，导致 observer 误判多次重启。固定方案是 `boot_signatures: ["rst:0x"]`，已成为 RISC-V ESP32 的标准配置。

2. **I2C 控制器类型决定 driver 版本**：C6 的 LP I2C 不能使用 V2 slave，只有 HP I2C 支持。规划 I2C loopback 时须先确认目标控制器是否具备 SCL stretch HW。

3. **Wi-Fi 双频需显式开启**：ESP32-C6 支持 5GHz，但 `WIFI_INIT_CONFIG_DEFAULT()` 后不会自动扫描 5GHz，需调用 `esp_wifi_set_band_mode()` 显式开启。此 API 在 C3/S3 等单频板上不存在。

---

## 7. 文件变更清单

| 文件/目录 | 变更类型 | 说明 |
|-----------|----------|------|
| `firmware/targets/esp32c6_devkit/` | 新增 | 14 个独立测试固件 + common 组件 |
| `tests/plans/esp32c6_devkit/` | 新增 | 14 个测试计划 JSON |
| `packs/esp32c6_devkit_{stage0,stage1,stage2,full}.json` | 新增 | 分 stage 运行用 pack |
| `configs/boards/esp32c6_devkit_dual_usb.yaml` | 更新 | flash port 修正为 CH341 fallback |
| `CLAUDE.md` | 更新 | 新增 CE `64b74cc2` 为 HIGH_PRIORITY 资产 |

---

## 8. Summary

ESP32-C6 DevKit Rule-B suite 是项目中首个完成 Rule-B 迁移的 RISC-V ESP32 板，在 2026-03-25 完成全部 13/13 PASS。

**最重要的贡献是两个可复用 pattern**：

1. **RISC-V boot_signatures fix（CE `64b74cc2`）**：发现并修复了 RISC-V ESP32 family 的观察器误判问题，该 pattern 被后续 C3、C5 全部直接复用，节省了重复探索。

2. **HP I2C V2 slave + bit-bang master（复用 CE `87240d79`）**：C6 与 C5 同样面对"只有一个 HP I2C 可用"的约束，直接应用 C5 的解决方案。

ESP32-C6 的 bring-up 验证了 Rule-B 架构的可迁移性：同一套 common 组件结构 + 同一套 staged testing 流程可被后续所有 ESP32 板型直接继承。
