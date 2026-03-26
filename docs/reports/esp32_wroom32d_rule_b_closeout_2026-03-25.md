# ESP32-WROOM-32D Rule-B Suite 完成报告

**日期：** 2026-03-25
**作者：** Claude (AI) + ali
**主要 Commits：**
- `7c4edcf` — "Refactor ESP32-WROOM-32D: one test per program (staged bring-up rule)"
- `2c2b178` — "Record ESP32-WROOM-32D refactored suite run results (12/12 PASS)"
- `28b6610` — "Add Rule D full suite firmware + update rule doc + label truth_layer"
- `fe97f6fb` — "Fix test_full_suite build: \*/ in comment closes block comment"
- `a1688d8` — "Promote esp32_wroom32d_cp210x to golden suite (bench-validated)"

---

## 1. 工作概述

ESP32-WROOM-32D（经典 ESP32 Xtensa 双核，CP210X UART 桥）的测试架构从旧的单体固件重构为 Rule-B 架构（每个测试一个独立 IDF 程序），并在 2026-03-25 完成所有 12 项测试 PASS，最终晋升为 Golden Suite。

本板为项目中首个使用经典 ESP32（Xtensa LX7 双核，IDF target=esp32）的 Rule-B 套件，有别于 RISC-V 系列（C3/C5/C6）。

---

## 2. 测试套件结构

### 2.1 架构分层

```
Stage 0  ─ hello              (bare-board smoke，无需接线)
Stage 1  ─ nvs / wifi / ble / sleep / pwm         (无需外部跳线)
Stage 2  ─ gpio_intr / pcnt / uart / adc / spi / i2c  (需要跳线)
Rule D   ─ test_full_suite    (12 个子测试合并为一个固件，convenience layer)
```

**注意：ESP32-WROOM-32D 无内部温度传感器**（该外设仅存在于较新的 ESP32 变体及 RISC-V 系列），因此共 12 项测试（C6 有 13 项，多一个 temp）。

### 2.2 测试清单

| 测试名 | Stage | 作用 | 设计要点 |
|--------|-------|------|----------|
| `hello` | 0 | 最小烟测：验证 CP210X 串口、IDF 启动、console 输出 | 输出 `AEL_HELLO board=ESP32WROOM PASS` |
| `test_nvs` | 1 | NVS Flash 读写校验 | `ael_common_init()` 初始化 nvs_flash |
| `test_wifi` | 1 | Wi-Fi 2.4GHz 被动扫描，ap_count ≥ 1 | 经典 ESP32 仅支持 2.4GHz（无双频 API） |
| `test_ble` | 1 | BLE 被动扫描 3 秒，advertisers ≥ 1 | NimBLE passive scan，测后调用 stop/deinit |
| `test_sleep` | 1 | Light sleep 1 秒 + 定时器唤醒 | 验证低功耗路径 |
| `test_pwm` | 1 | LEDC 1 kHz / 50% duty on GPIO4，配置成功即 PASS | GPIO4 不需跳线 |
| `test_gpio_intr` | 2 | GPIO25→GPIO26 20 次上升沿中断计数 | INTR 必须在 PCNT 之前（共享 GPIO25/26） |
| `test_pcnt` | 2 | GPIO25 驱动 100 脉冲，GPIO26 PCNT 计数校验 = 100 | 依赖 INTR 释放 GPIO26 |
| `test_uart` | 2 | UART1 loopback GPIO17→GPIO16，发 "AEL_UART_PING" 收回校验 | UART1（非 UART0 console） |
| `test_adc` | 2 | GPIO33 drive HIGH/LOW → GPIO34 (ADC1_CH6) 读值，hi>2000/lo<500 | GPIO34 为 input-only pin，仅用于读取 ADC |
| `test_spi` | 2 | SPI2 MOSI=GPIO23↔MISO=GPIO19 loopback，8 字节比较 | CLK=GPIO18, CS=GPIO5 |
| `test_i2c` | 2 | HW I2C0 master (GPIO21/22) + HW I2C1 slave V1 (GPIO13/14) | **关键设计决策，见第 3 节** |
| `test_full_suite` | Rule D | 以上 12 个子测试顺序执行 | sub_gpio_intr → gpio_reset_pin(GPIO26) → sub_pcnt |

### 2.3 接线要求（Stage 2 及 full_suite）

| 跳线 | 用途 |
|------|------|
| GPIO25 ↔ GPIO26 | GPIO interrupt drive / PCNT input（共用） |
| GPIO17 ↔ GPIO16 | UART1 TX → RX loopback |
| GPIO33 → GPIO34 | ADC drive → ADC1_CH6 input |
| GPIO23 ↔ GPIO19 | SPI2 MOSI ↔ MISO loopback |
| GPIO21 ↔ GPIO13 | I2C0 SDA master ↔ I2C1 SDA slave |
| GPIO22 ↔ GPIO14 | I2C0 SCL master ↔ I2C1 SCL slave |

### 2.4 板卡 USB 配置

| 接口 | 设备 | 用途 |
|------|------|------|
| CP210X UART bridge | `/dev/ttyUSB0` | 烧录 + console（UART0 at 115200），RTS/DTR auto-reset |

ESP32-WROOM-32D 为 bridge_only（单 USB），无原生 USB。Flash 和 console 共用同一个 CP210X 串口。`reset_strategy: rts` 可靠。

---

## 3. 关键设计决策

### 3.1 I2C：HW I2C V1 driver（非 V2）

经典 ESP32 有两个 I2C 控制器（I2C0 和 I2C1），但**不支持 V2 slave driver**，原因是 V2 需要硬件 SCL stretch 支持，而经典 ESP32 I2C 硬件不具备此特性。

**方案**：HW I2C0 master（GPIO21/22）+ HW I2C1 slave V1 API（GPIO13/14）。
- Slave 使用 `i2c_slave_config_t`（V1 结构体），`on_recv_done` 回调
- `i2c_slave_receive()` 须在 `bus_reset()` 之后调用，避免过早触发回调

**与 C6 的对比**：C6 只有 1 个 HP I2C，必须 bit-bang master；WROOM-32D 有 2 个 HW I2C，但因 V2 不可用，选用 V1。两者的约束来源不同，解法也不同。

### 3.2 Rule B 架构（与旧 monolithic 的区别）

旧版：`firmware/targets/esp32_wroom32d_suite/`——单一程序，11 个测试串联，已删除。
新版：`firmware/targets/esp32_wroom32d/`——12 个独立程序 + common 组件，每个程序独立编译、独立验证。

旧版套件存在的问题：
- 单程序状态污染（某个驱动初始化失败会影响后续测试）
- 无法单独重跑某一测试
- 证据链不完整（无法判断单项通过/失败）

### 3.3 init 顺序

```
ael_common_init() → ael_gpio_isr_init() → ael_netif_init()
```
此顺序为经典 ESP32 已知正确顺序：GPIO ISR service 在 WiFi/NimBLE 之前注册，避免 ISR 资源竞争。在 full_suite 中统一由 `app_main()` 顶层完成初始化，各 sub_XXX() 直接使用。

### 3.4 GPIO34 为 input-only pin

ESP32 GPIO34–GPIO39 为 input-only pins（无驱动能力）。ADC 测试中 GPIO33 作为驱动输出，GPIO34 作为 ADC1_CH6 输入。在 board config 的 `safe_output` 中已排除 GPIO34–GPIO39。

---

## 4. 遇到的问题与解决过程

### 问题一：test_full_suite 编译失败 — `*/` 注释提前闭合 block comment

**现象**：`test_full_suite` 首次提交后编译报错，IDF 构建日志提示语法错误。

**根本原因**：固件注释中出现了 `*/` 字符序列（如描述 bit-bang master 时写了 `/* ... bit-bang */...`），被 C 编译器提前解析为 block comment 的结束符，导致注释之后的代码被当作 comment 内容，引发语法错误。

**解决方案**：将注释中的 `*/` 替换为不触发 block comment 的写法（如 `* /` 或改用行注释 `//`）。在 commit `fe97f6fb` 中修复。

**教训**：在固件注释中描述 bit-bang 或 I2C 协议时须注意 C 注释语法，避免意外闭合 block comment。

### 问题二：I2C V2 slave 不可用

**现象**：初版 test_i2c 尝试使用 V2 slave API（`CONFIG_I2C_ENABLE_SLAVE_DRIVER_VERSION_2=y`），编译通过但运行时 `i2c_new_slave_device()` 返回 `ESP_ERR_NOT_SUPPORTED`。

**根本原因**：经典 ESP32 I2C 硬件缺少 SCL stretch 支持，V2 driver 在 runtime 检测到后拒绝初始化。

**解决方案**：改用 V1 API（`i2c_slave_config_t`），同时从 `sdkconfig.defaults` 中移除 `CONFIG_I2C_ENABLE_SLAVE_DRIVER_VERSION_2=y`（此配置仅适用于支持该特性的芯片，如 C5/C6/S3）。

### 问题三：`i2c_slave_receive()` 过早触发回调

**现象**：V1 slave 初始化完成后，master 发送数据前 `on_recv_done` 回调已触发，数据为空。

**根本原因**：在 slave 初始化后立即调用 `i2c_slave_receive()` 注册接收缓冲区，I2C 总线上可能存在残留状态导致立即回调。

**解决方案**：在 `i2c_slave_receive()` 之前调用 `i2c_master_bus_reset()`（V1 bus reset），清除总线残留状态，确保 slave 在干净状态下等待 master 发送。

### 问题四：Golden Promotion 门控验证

本次首次走完完整的 golden promotion 流程：
1. flash 验证（CP210X 烧录，`reset_strategy=rts`）
2. truth layer 12 个独立程序各自 PASS
3. convenience layer `test_full_suite` PASS（run_id: `2026-03-25_17-51-56`）
4. PROMOTION.md 更新（`lifecycle_stage: merge_candidate`）
5. `default_verification_setting.yaml` 新增为 optional 步骤
6. `default_verification_baseline.md` 更新（optional candidates 2→3）

---

## 5. 最终测试结果

### 独立测试（Truth Layer）：12/12 PASS

| Stage | 测试 | 结果 |
|-------|------|------|
| 0 | hello | PASS |
| 1 | test_nvs | PASS |
| 1 | test_wifi | PASS |
| 1 | test_ble | PASS |
| 1 | test_sleep | PASS |
| 1 | test_pwm | PASS |
| 2 | test_gpio_intr | PASS |
| 2 | test_pcnt | PASS |
| 2 | test_uart | PASS |
| 2 | test_adc | PASS |
| 2 | test_spi | PASS |
| 2 | test_i2c | PASS |

### Full Suite（Convenience Layer）：12/12 PASS

```
AEL_SUITE_FULL DONE passed=12 failed=0
run_id: 2026-03-25_17-51-56_esp32_wroom32d_cp210x_test_full_suite
```

### Golden Promotion

2026-03-25 完成 Golden Suite 晋升，加入 `default_verification_setting.yaml` 作为 optional 步骤。

---

## 6. 经验与技能，CE 写入情况

### 写入 CE 的条目

本次 bring-up 过程中，WROOM-32D 特有的经验（V1 I2C driver、bus_reset 技巧）已通过 task 级别条目记录，未单独提升为 pattern 级别（因为经典 ESP32 V1 I2C 的使用场景相对特殊，不如 V2/bit-bang 方案通用）。

| CE ID | scope | 内容摘要 |
|-------|-------|----------|
| `538cf39c` | task | WROOM-32D suite success 记录 |
| `e47bc5cd` | task | WROOM-32D test_full_suite success 记录 |

### 复用的已有 CE Pattern

| CE ID | 内容 | 本次应用 |
|-------|------|----------|
| `933fc74a` | Minimal-Instrument Board Bring-up Pattern | 整体 staged bring-up 流程框架 |
| `7daa8c80` | ESP32 USB 接口分类 | 确认 WROOM-32D 为 bridge_only，无原生 USB |

### 关键教训

1. **经典 ESP32 无温度传感器**：ESP32（Xtensa）内置温度传感器在一些 ESP32-D0WDQ6 版本上存在但精度极低，不适合作为测试依据。项目选择不包含 temp 测试，保持 12 项（区别于 C6/C3 的 13/10 项）。未来新板 bring-up 时须确认该芯片是否有可靠的内部温度传感器 API。

2. **I2C driver 版本必须与芯片硬件匹配**：V2 slave 需要 SCL stretch HW（仅 ESP32-S3/C5/C6 等较新芯片支持），经典 ESP32 必须使用 V1。在 Rule-B 迁移过程中，应先查 CE / IDF 文档确认 driver 版本，避免运行时失败。

3. **C 注释中的 `*/` 会提前闭合 block comment**：在描述 bit-bang 协议或 I2C 时序时，`*/` 字符序列必须避免出现在 `/* ... */` 注释内部。使用行注释 `//` 或将 `*` 与 `/` 分开书写。

4. **CP210X bridge 的 RTS/DTR reset 非常可靠**：与原生 USB 不同，CP210X bridge 的 `reset_strategy: rts` 在所有测试中均无异常，不需要 Errno 71 容错逻辑。经典 ESP32 + UART 桥是最稳定的 flash/reset 方案。

5. **`i2c_slave_receive()` 须在 bus_reset 后调用**：即便总线初始化成功，残留的 I2C 总线状态可能触发虚假的 slave 接收回调。标准流程：`i2c_new_master_bus()` → `i2c_master_bus_reset()` → `i2c_slave_receive()`。

---

## 7. 文件变更清单

| 文件/目录 | 变更类型 | 说明 |
|-----------|----------|------|
| `firmware/targets/esp32_wroom32d/` | 重构新增 | 旧 monolithic 套件删除，新 12 个独立程序 + common |
| `tests/plans/esp32_wroom32d/` | 重构新增 | 13 个测试计划 JSON（含 full_suite）|
| `packs/esp32_wroom32d_{stage0,stage1,stage2,full}.json` | 新增 | 分 stage 运行用 pack |
| `assets_golden/duts/esp32_wroom32d_cp210x/PROMOTION.md` | 更新 | lifecycle_stage: merge_candidate → 晋升记录 |
| `configs/known_boards.yaml` | 更新 | esp32_wroom32d_cp210x golden status |
| `default_verification_setting.yaml` | 更新 | 新增 optional step |
| `docs/default_verification_baseline.md` | 更新 | optional candidates 计数更新 |
| `docs/rules/esp32_staged_bringup_isolated_test.md` | 更新 | 统一 4-rule 架构文档（A/B/C/D），增加 truth/convenience layer 定义 |

---

## 8. Summary

ESP32-WROOM-32D Rule-B suite 在 2026-03-25 完成全部 12/12 PASS 并晋升为 Golden Suite。

**本次工作的三个关键价值：**

1. **确立 Rule-B 架构文档**：在 `docs/rules/esp32_staged_bringup_isolated_test.md` 中统一了 A/B/C/D 四规则体系，并引入 Truth Layer / Convenience Layer 的明确区分，为后续 C3、C6、S3 等板型的 Rule-B 迁移提供了参考规范。

2. **经典 ESP32 I2C V1 loopback 方案固化**：HW I2C0 master + HW I2C1 slave V1 + `bus_reset()` + `i2c_slave_receive()` 是经典 ESP32 的稳定 I2C loopback 方案，区别于 RISC-V 系列（需 V2 或 bit-bang）。

3. **Golden Promotion 完整流程验证**：WROOM-32D 是首批走完完整 Golden Promotion 门控（truth layer + convenience layer + default_verification_setting 注册）的 ESP32 板，为后续板型的晋升流程提供了模板。
