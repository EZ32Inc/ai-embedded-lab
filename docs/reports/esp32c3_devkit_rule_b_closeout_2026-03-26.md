# ESP32-C3 DevKit Rule-B Suite 完成报告

**日期：** 2026-03-26
**作者：** Claude (AI) + ali
**Commit：** `25bba4e` — "Add ESP32-C3 DevKit Rule-B suite: 11 isolated tests + full_suite (10/10 PASS)"

---

## 1. 工作概述

本次工作将 ESP32-C3 DevKit 从旧的单体固件架构（Rule A/monolithic）迁移至 Rule-B 架构（每个测试一个独立 IDF 程序），并完成全部 10 项功能测试 + 1 个 full_suite 聚合测试，最终结果 **10/10 PASS**。

旧架构痕迹：`firmware/targets/esp32c3_suite/` + `tests/plans/esp32c3_suite.json`（已发现存在验证假阳性问题，见第 4 节）。
新架构落地：`firmware/targets/esp32c3_devkit/` + `tests/plans/esp32c3_devkit/`。

---

## 2. 测试套件结构

### 2.1 架构分层

```
Stage 0  ─ hello              (bare-board smoke，无需接线)
Stage 1  ─ nvs / temp / wifi / ble / sleep / pwm   (无需外部跳线)
Stage 2  ─ gpio_intr / uart / adc / spi             (需要跳线)
Rule D   ─ test_full_suite     (10 个子测试合并为一个固件，convenience layer)
```

Truth Layer（真相层）：11 个独立程序，每个程序独立编译、独立验证。
Convenience Layer（便捷层）：`test_full_suite`，一次烧录跑完全部 10 项。

### 2.2 测试清单

| 测试名 | Stage | 作用 | 设计要点 |
|--------|-------|------|----------|
| `hello` | 0 | 最小烟测：验证 USB CDC 枚举、IDF 启动、printf 输出 | 无依赖，仅 printf + 死循环 |
| `test_nvs` | 1 | NVS Flash 读写：写入 `0xAE1C0001`，读回校验 | `ael_common_init()` 内完成 nvs_flash_init |
| `test_temp` | 1 | 内部温度传感器：读取摄氏度，校验 5–90°C 范围 | 验证芯片内置传感器功能 |
| `test_wifi` | 1 | Wi-Fi 被动扫描：验证 RF 链路，ap_count ≥ 1 | 仅扫描，不连接 AP |
| `test_ble` | 1 | BLE 被动扫描：NimBLE passive scan 3 秒，advertisers ≥ 1 | 测后调用 nimble_port_stop/deinit 清理 |
| `test_sleep` | 1 | Light sleep 1 秒 + 定时器唤醒，校验 wakeup cause | 验证低功耗路径 |
| `test_pwm` | 1 | LEDC 1 kHz / 50% duty cycle on GPIO8，配置成功即 PASS | 无法外部量测，验证 driver 配置 |
| `test_gpio_intr` | 2 | GPIO4→GPIO5 触发 20 次上升沿中断，计数验证 | INTR 必须在 PCNT 之前（共享 pin） |
| `test_uart` | 2 | UART1 loopback GPIO6→GPIO7，发 "AEL_UART_PING" 收回校验 | 验证 UART 发送/接收路径 |
| `test_adc` | 2 | GPIO8 驱动 HIGH/LOW → GPIO1 (ADC1_CH1) 读值，hi>2000 / lo<500 | **GPIO8 替代 GPIO2**（见第 4 节） |
| `test_spi` | 2 | SPI2 MOSI=GPIO10↔MISO=GPIO3 loopback，8 字节 `0xA5..0x34` 比较 | DMA=SPI_DMA_CH_AUTO |
| `test_full_suite` | Rule D | 以上 10 个子测试顺序执行，输出 `AEL_SUITE_FULL DONE passed=10 failed=0` | GPIO8 dual-use：PWM→GPIO output 需 `gpio_reset_pin` |

### 2.3 接线要求（Stage 2 及 full_suite）

| 跳线 | 用途 |
|------|------|
| GPIO4 ↔ GPIO5 | GPIO interrupt drive → input |
| GPIO6 ↔ GPIO7 | UART1 TX → RX loopback |
| **GPIO8 → GPIO1** | ADC drive → ADC1_CH1（注意：非 GPIO2！） |
| GPIO10 ↔ GPIO3 | SPI2 MOSI ↔ MISO loopback |

### 2.4 板卡 USB 配置

| 接口 | 设备 | 用途 |
|------|------|------|
| Native USB Serial/JTAG | `/dev/ttyACM1`（MAC `B0:81:84:BF:F6:D0`） | 烧录 + console 输出 |

ESP32-C3 为 Class B 仅原生 USB 板（无 CH341 桥）。Console 和 Flash 共用同一个 CDC 端口。

---

## 3. 关键设计决策

### 3.1 Rule-B 架构（一测一程序）

每个测试独立编译，共享 `firmware/targets/esp32c3_devkit/common/` 组件：
- `ael_board/ael_board_init.h` — 封装 `ael_common_init()` / `ael_gpio_isr_init()` / `ael_netif_init()`
- `sdkconfig.defaults` — 全套 BT/WiFi/NVS/I2C V2/8192 stack 配置
- `partitions.csv` — 自定义分区表（nvs 24K + phy_init 4K + factory 1920K）

优点：单个测试失败不污染其他测试状态；构建隔离；便于单独重跑。

### 3.2 test_full_suite 中 GPIO8 双重使用

`test_full_suite` 中 GPIO8 先被 LEDC（PWM 测试）占用，再被 ADC 测试当作驱动输出。
解决方式：在 `sub_adc()` 入口调用 `gpio_reset_pin(GPIO_NUM_8)` 将 GPIO8 从 LEDC 释放后，重新 `gpio_config` 为普通输出。

### 3.3 INTR 在 PCNT 之前的顺序约束

GPIO4/GPIO5 被 GPIO interrupt 和 PCNT 共用。一旦 PCNT 通道注册到 GPIO5，该 pin 被 PCNT peripheral 锁定，后续 GPIO ISR 无法再使用。因此 full_suite 中 `sub_gpio_intr()` 必须在 `sub_pcnt()` 之前执行，执行完后调用 `gpio_reset_pin(INTR_INPUT)` 释放。

---

## 4. 遇到的问题与解决过程

### 问题一：test_sleep 烧录后报 `[Errno 71] Protocol error`

**现象：** `esptool` 烧录完成后抛出 `OSError: [Errno 71] Protocol error`，AEL 判定为烧录失败，测试无法继续。

**根本原因：** ESP32-C3 原生 USB CDC 在 `--after hard_reset` 时，芯片立即 reset 导致 USB 端口断开。`esptool` 随后在已断开的端口上调用 `_setRTS(False)` 清理，引发 `Protocol error`。**实际上，烧录数据在报错之前已经写入并校验完毕**（log 中出现 `"Leaving..."` + `"Hash of data verified"`）。

**解决方案：** 在 `ael/adapters/flash_idf.py` 的 `CalledProcessError` 捕获块中增加判断：若 combined stdout+stderr 同时包含 `"Leaving..."` 和 `"[Errno 71]"` 或 `"Protocol error"`，视为成功，不报错。

**教训：** 框架级修复，适用于所有 ESP32 原生 USB 目标。已写入 CE（见第 6 节）。

---

### 问题二：ADC 测试 GPIO2 始终读值为 0（无法 drive HIGH）

**现象：** `test_adc` 中将 GPIO2 设为输出并置 HIGH，随即读取 ADC1_CH1（GPIO1）——读值始终 ≈ 0，`raw_hi=22`。

**排查过程：**
1. 尝试调整初始化顺序（先 GPIO 后 ADC）——无效。
2. 尝试调用 `gpio_reset_pin(GPIO_NUM_2)` 后重配置——无效。
3. 加诊断代码：`GPIO2_RAW set=1 read=0`——GPIO2 置高后立即读回为 0，说明问题在 GPIO2 本身，与 ADC 无关。

**根本原因（ESP32-C3 LP-IO 硬件限制）：**
ESP32-C3 的 GPIO0–GPIO4 属于低功耗 IO（LP-IO），与 ADC1 共享模拟通路。一旦调用 `adc_oneshot_new_unit(ADC_UNIT_1)` 初始化 ADC1 单元，ADC 模拟前端会将这些 pin 的数字驱动电路 suspend，导致 `gpio_set_level(GPIO2, 1)` 写入后硬件仍输出 LOW。此为芯片级硬件行为，软件无法绕过。

**发现过程（假阳性调查）：** 用户反映旧版套件（pre-refactor）使用 GPIO2→GPIO1 接线且测试通过。深入调查发现旧版 AEL 验证存在 bug——该次运行实际只采集到 3 行输出（`AEL_SUITE_C3 BOOT` + `AEL_TEMP`），`missing_expect: []` 判为空导致误报 `ok: true`。旧的"通过"是假阳性，从未真正验证过 ADC。

**解决方案：** 将 ADC 驱动引脚从 GPIO2 改为 GPIO8（非 LP-IO，非 ADC capable）。
- `test_adc/main/main.c`：`ADC_DRIVE = GPIO_NUM_8`
- `test_full_suite/main/main.c`：`ADC_DRIVE = GPIO_NUM_8` + `gpio_reset_pin` 释放 LEDC 占用
- 测试计划和 pack 接线描述同步更新（GPIO2→GPIO1 改为 GPIO8→GPIO1）

**验证结果：** `raw_hi=4095 raw_lo=0`，明确 PASS。

**教训：** 该限制为 ESP32-C3 硬件特性，未在 IDF 文档中显著提示。所有未来使用 ESP32-C3 ADC 的测试均须使用 GPIO5+ 作为驱动引脚。已写入 CE（见第 6 节）。

---

### 问题三：`--before default_reset` 偶发 "device reports readiness to read but returned no data"

**现象：** 连续多次快速烧录后，某次烧录因 USB 时序问题失败，提示端口准备好读取但无数据返回。

**根本原因：** 连续 reset 后 USB CDC 枚举需要时间，某些情况下 esptool 尝试连接时端口还未就绪。

**解决方案：** 等待片刻后重试，问题自然消失。尝试过 `CONFIG_ESPTOOLPY_BEFORE_NORESET=y` 但会导致 "Write timeout"（固件未进入 download mode）。不需要专项修复，属于偶发时序问题。

---

### 问题四：旧 boot_signatures 匹配失败

**现象（引用 CE pattern `64b74cc2`）：** RISC-V ESP32 正常启动会输出 4 条包含 `boot:` 字样的 ROM 日志，AEL observer 若以 `"boot:"` 为启动签名，会在同一次正常启动内多次触发，导致误判为崩溃/重启。

**解决方案：** 所有 ESP32-C3 测试计划使用 `"boot_signatures": ["rst:0x"]`，该字符串只在真正复位事件后出现一次。此 pattern 已收录在 CE `64b74cc2`（HIGH_PRIORITY），本次直接复用。

---

## 5. 最终测试结果

### 独立测试（Truth Layer）：11/11 PASS

| 测试 | 结果 | 关键输出 |
|------|------|----------|
| hello | PASS | `AEL_HELLO board=ESP32C3 PASS` |
| test_nvs | PASS | `AEL_NVS wrote=0xAE1C0001 read=0xAE1C0001 PASS` |
| test_temp | PASS | `AEL_TEMP celsius=XX.X PASS` |
| test_wifi | PASS | `AEL_WIFI ap_count=N PASS` (N≥1) |
| test_ble | PASS | `AEL_BLE advertisers=N PASS` (N≥1) |
| test_sleep | PASS | `AEL_SLEEP wakeup_cause=4 PASS` |
| test_pwm | PASS | `AEL_PWM gpio=GPIO8 freq_hz=1000 duty_pct=50 PASS` |
| test_gpio_intr | PASS | `AEL_INTR triggered=20 expected=20 PASS` |
| test_uart | PASS | `AEL_UART sent=13 recv=13 PASS` |
| test_adc | PASS | `AEL_ADC raw_hi=4095 raw_lo=0 PASS` |
| test_spi | PASS | `AEL_SPI len=8 match=1 err=0 PASS` |

### Full Suite（Convenience Layer）：10/10 PASS

```
AEL_SUITE_FULL DONE passed=10 failed=0
```

（hello 不计入 full_suite 子测试数，故 10 而非 11）

### Pack 回归验证（commit 后再次运行）：12/12 PASS

Pack `esp32c3_devkit_full.json` 包含所有 12 个测试计划，2026-03-26 commit 后完整重跑全部通过。

---

## 6. 经验与技能，CE 写入情况

### 写入 CE 的条目

| CE ID | scope | 内容摘要 |
|-------|-------|----------|
| `f5aa5241` | pattern（HIGH_PRIORITY） | ESP32-C3 LP-IO GPIO0-GPIO4：ADC1 激活后无法输出 HIGH，须使用 GPIO5+ 作为驱动引脚 |
| `a4adfb05` | pattern（HIGH_PRIORITY） | ESP32 原生 USB 烧录 Errno 71：含 `Leaving...` 时视为成功，框架级修复（`flash_idf.py`） |
| `01086f19` | board_family | ESP32-C3 DevKit Rule-B suite 完整记录：接线、约束、通过结论 |

### 本次复用的已有 CE Pattern

| CE ID | 内容 | 本次应用 |
|-------|------|----------|
| `64b74cc2` | RISC-V boot_signatures 必须用 `rst:0x` | 所有 C3 测试计划 |
| `7daa8c80` | ESP32 USB 接口分类（Class A dual / Class B native-only） | 确认 C3 为 Class B，flash port = console port = `/dev/ttyACM1` |

### 关键教训总结

1. **LP-IO 限制是芯片硬件约束，非软件 bug**：ESP32-C3 GPIO0–GPIO4 一旦 ADC1 激活即无法数字输出 HIGH，任何软件绕过（`gpio_reset_pin`、调整初始化顺序）均无效。规则：**ADC loopback 驱动引脚必须选 GPIO5 以上**。

2. **旧验证结果不可信，需追查 missing_expect**：旧版 C3 套件的假阳性暴露了一个系统性问题——`missing_expect: []` 并不意味着所有 pattern 都被匹配，可能是因为 observer 根本没有捕获到足够的输出。诊断时应同时检查 `captured_lines` 数量。

3. **Errno 71 是预期行为，不是错误**：原生 USB 固件在 hard_reset 后 USB 断开，这是正常的。框架需要容忍清理阶段的这类错误，以 `"Leaving..."` 为成功标志，不以清理阶段是否报错为标志。

4. **GPIO 双重使用须显式释放**：在同一个 full_suite 固件中，若一个 GPIO 先被外设（如 LEDC）占用，再被普通 GPIO 驱动使用，必须在两者之间调用 `gpio_reset_pin()` 显式释放外设所有权。

5. **测试顺序约束（INTR 先于 PCNT）**：共享 GPIO 的不同 peripheral 有占用锁。GPIO ISR 注册后必须在 PCNT 注册前完成并释放 pin，否则 PCNT 会锁定 pin 导致后续 ISR 操作失败。

---

## 7. 文件变更清单

| 文件/目录 | 变更类型 | 说明 |
|-----------|----------|------|
| `firmware/targets/esp32c3_devkit/` | 新增 | 11 个独立测试固件 + common 组件，共 ~45 个文件 |
| `tests/plans/esp32c3_devkit/` | 新增 | 12 个测试计划 JSON |
| `packs/esp32c3_devkit_full.json` | 新增 | 包含全部 12 个测试计划的 pack |
| `packs/esp32c3_devkit_stage0/1/2.json` | 新增 | 分 stage 运行用 pack |
| `packs/esp32c3_full_suite.json` | 更新 | 指向新 Rule-B 计划（原指向旧 monolithic） |
| `configs/boards/esp32c3_devkit_native_usb.yaml` | 更新 | flash port 修正为 `/dev/ttyACM1` |
| `ael/adapters/flash_idf.py` | 更新 | Errno 71 容忍逻辑（框架级修复） |
| `ael/civilization/data/run_index.json` | 更新 | 记录 C3 full_suite 成功 |

---

## 8. Summary

ESP32-C3 DevKit Rule-B suite 从零开始完成，历经三个阶段：

**Phase 1（框架修复）**：发现并修复 `flash_idf.py` 中原生 USB Errno 71 问题，使烧录流程对 C3 原生 USB 端口断开行为具备鲁棒性。

**Phase 2（Stage 0+1）**：hello + nvs + temp + wifi + ble + sleep + pwm 共 7 个测试顺利通过，无硬件障碍。

**Phase 3（Stage 2 + Full Suite）**：发现 ESP32-C3 LP-IO ADC1 硬件限制（GPIO0–GPIO4 在 ADC1 激活后无法输出 HIGH），将 ADC 驱动引脚从 GPIO2 改为 GPIO8，同时解决 full_suite 中 GPIO8 LEDC→GPIO 双重使用问题。最终 10/10 PASS。

**验证质量**：本次套件纠正了旧版套件（pre-refactor）的假阳性——旧版从未真正验证 ADC，当前 Rule-B 架构每个测试独立可追溯，证据链完整。

**CE 资产沉淀**：2 条 HIGH_PRIORITY pattern（LP-IO ADC 限制、Errno 71 flash 容忍）已写入 CE，可直接应用于未来所有 ESP32-C3/C6 等相关 bring-up 任务。
