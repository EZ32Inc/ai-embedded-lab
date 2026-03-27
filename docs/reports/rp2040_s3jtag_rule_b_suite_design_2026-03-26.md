# RP2040 + S3JTAG Rule-B Suite 设计草案

**日期：** 2026-03-26
**参考规则：** `docs/rules/esp32_staged_bringup_isolated_test.md`
**参考报告：** `docs/reports/esp32c3_devkit_rule_b_closeout_2026-03-26.md`、`docs/reports/esp32s3_devkit_rule_b_closeout_2026-03-26.md`
**目标：** 将当前 `RP2040 + S3JTAG` 验证路径整理为符合 Rule A/B/C/D 的 Golden Suite 结构，而不是停留在若干独立 pack 和 closeout。

---

## 1. 工作概述

当前 `RP2040 + S3JTAG` 已经完成了以下真实 bench 能力验证：
- SWD 探测和烧录
- mailbox/minimal runtime gate
- TARGETIN 单线数字信号验证（low / high / 100 Hz / 1 kHz）
- internal Web UART banner 验证

这些能力已经足够支撑一套 Rule-B 风格测试架，但资产组织方式还没有完全对齐 `docs/rules/esp32_staged_bringup_isolated_test.md` 中的四条规则：
- Rule A — No-Wire Console-First Validation
- Rule B — One Test, One Program
- Rule C — Stage by Dependency
- Rule D — Optional Full Board Suite

最重要的修正是：
- 凡是需要任何人工跳线的测试，都不应放在 Stage 1
- 当前 `TARGETIN` low/high/100Hz/1kHz 需要人工接线，因此应归入 Stage 2
- Stage 1 必须只保留真正无额外接线的 no-wire self-tests

---

## 2. Rule-B 目标结构

### 2.1 架构分层

建议的 RP2040 Rule-B 套件结构：

```text
Stage 0  ─ hello / minimal_runtime_mailbox        (最小 bring-up，无额外接线)
Stage 1  ─ no-wire self-tests                     (内部能力验证，无额外接线)
Stage 2  ─ TARGETIN / UART / SPI / I2C / ADC / PWM integration tests
Rule D   ─ test_full_suite 或等价 full pack
```

Truth Layer（真相层）：
- 每个测试独立程序、独立 plan、独立 PASS/FAIL

Convenience Layer（便捷层）：
- stage packs
- full pack
- 可选 combined `test_full_suite`

### 2.2 Rule A / Rule B / Rule C / Rule D 对应解释

#### Rule A — Stage 0
必须先有一个最小 bring-up 测试，验证：
- RP2040 可被 S3JTAG 通过 SWD 烧录
- 板子能稳定启动
- 存在确定性的最小可观测 PASS 信号

对 `RP2040 + S3JTAG`，当前最接近 Rule A 的已验证资产是：
- `minimal_runtime_mailbox_s3jtag`

长期更理想的形态仍然是一个显式 `hello_s3jtag`，但在它落地前，`minimal_runtime_mailbox_s3jtag` 可以作为当前 Stage 0 的 hello-equivalent。

#### Rule B — One Test, One Program
每个测试必须独立：
- 单独 firmware asset
- 单独 test plan
- 单独 PASS/FAIL
- 能单独 rerun / debug

#### Rule C — Stage by Dependency
测试要按依赖分层：
- 先最小 bring-up
- 再真正 no-wire 的自测
- 再所有需要人工接线的 integration tests

#### Rule D — Optional Full Suite
在 truth layer 稳定后，允许引入：
- `full pack`，由 runner 顺序编排全部单测
- 或 combined firmware `test_full_suite`

但 full suite 必须是 convenience layer，不得替代 truth layer。

---

## 3. 当前 RP2040 资产盘点

### 3.1 已有 S3JTAG test plans

当前已存在：
- `tests/plans/rp2040_minimal_runtime_mailbox_s3jtag.json`
- `tests/plans/rp2040_gpio_level_low_with_s3jtag.json`
- `tests/plans/rp2040_gpio_level_high_with_s3jtag.json`
- `tests/plans/rp2040_gpio_signature_100hz_with_s3jtag.json`
- `tests/plans/rp2040_gpio_signature_with_s3jtag.json`
- `tests/plans/rp2040_uart_banner_with_s3jtag.json`

另有泛用 RP2040 计划（尚未适配 S3JTAG Stage 2）：
- `tests/plans/rp2040_uart_banner.json`
- `tests/plans/rp2040_spi_banner.json`
- `tests/plans/rp2040_i2c_banner.json`
- `tests/plans/rp2040_adc_banner.json`
- `tests/plans/rp2040_gpio_signature.json`

### 3.2 已有 packs

当前已存在：
- `packs/smoke_rp2040_s3jtag.json`
- `packs/standard_rp2040_s3jtag.json`
- `packs/uart_rp2040_s3jtag.json`
- `packs/rp2040_s3jtag_stage0.json`
- `packs/rp2040_s3jtag_stage1.json`
- `packs/rp2040_s3jtag_stage2.json`
- `packs/rp2040_s3jtag_full.json`

### 3.3 已有 golden firmware assets

当前已存在：
- `assets_golden/duts/rp2040_pico/minimal_runtime_mailbox_s3jtag/`
- `assets_golden/duts/rp2040_pico/gpio_level_low_s3jtag/`
- `assets_golden/duts/rp2040_pico/gpio_level_high_s3jtag/`
- `assets_golden/duts/rp2040_pico/gpio_signature_100hz_s3jtag/`
- `assets_golden/duts/rp2040_pico/gpio_signature_s3jtag/`
- `assets_golden/duts/rp2040_pico/uart_banner_s3jtag/`

现有泛用 firmware targets：
- `firmware/targets/rp2040_pico_adc/`
- `firmware/targets/rp2040_pico_spi/`
- `firmware/targets/rp2040_pico_i2c/`
- `firmware/targets/rp2040_pico_uart/`

### 3.4 已完成的正式 closeout

当前已存在：
- `docs/rp2040_s3jtag_gpio_validation_closeout_2026-03-26.md`
- `docs/rp2040_s3jtag_standard_suite_closeout_2026-03-26.md`
- `docs/rp2040_s3jtag_uart_validation_closeout_2026-03-26.md`
- `docs/skills/rp2040_s3jtag_signal_validation_skill_2026-03-26.md`
- `docs/skills/rp2040_s3jtag_uart_validation_skill_2026-03-26.md`

结论：
- truth-layer 资产已经有一大半
- 但 Stage 1/Stage 2 的边界需要重新按 wiring 规则收紧

---

## 4. 建议的 RP2040 Rule-B 测试清单

### 4.1 Stage 0

| 测试名 | 作用 | 观测方式 | 状态 |
|--------|------|----------|------|
| `test_minimal_runtime_mailbox` | 最小 bring-up，证明 SWD flash + deterministic runtime gate | mailbox | 已有，当前作为 Stage 0 hello-equivalent |
| `hello_s3jtag` | 更纯粹的 Rule-A hello | mailbox 或极简可观测信号 | 缺失，建议后补 |

说明：
- 在 dedicated `hello_s3jtag` 存在前，`minimal_runtime_mailbox_s3jtag` 应作为当前 Stage 0 基线
- 这一步不依赖 TARGETIN、UART、SPI、I2C、ADC 额外接线

### 4.2 Stage 1 — 真正无额外接线的 no-wire self-tests

下列测试更适合作为 RP2040 的 Stage 1 候选：

| 候选测试名 | 作用 | 为什么符合 Stage 1 |
|------------|------|--------------------|
| `test_internal_temp` | 读取 RP2040 内部温度传感器 | 无额外接线 |
| `test_pwm_led` | 驱动板载 LED（GPIO25）或内部定时 PWM 逻辑 | 无额外接线 |
| `test_timer_mailbox` | 定时器/心跳通过 mailbox 递增 | 无额外接线 |
| `test_flash_read` | 读取 XIP flash / JEDEC / 固件区数据一致性 | 无额外接线 |
| `test_watchdog_reboot` | 看门狗或受控 reboot 路径 | 无额外接线 |
| `test_sleep_alarm` | sleep / timer wake 验证 | 无额外接线 |

当前现实状态：
- **目前尚无已正式验证并纳入 S3JTAG truth layer 的 Stage 1 no-wire self-tests，除 Stage 0 基线外。**
- 因此，当前 Rule-B 结构里 Stage 1 应视为“待补的一层”，而不是把 TARGETIN 测试错误地塞进去。

### 4.3 Stage 2 — 所有需要人工接线的 integration tests

凡是需要额外跳线的测试，都应归入 Stage 2。

#### 当前已验证 Stage 2

当前 bench 已验证并固定下来的 Stage 2 接线契约是：
- `RP2040 GPIO18 -> S3JTAG GPIO15 / TARGETIN`
- `RP2040 GPIO0 -> S3JTAG GPIO7`
- `RP2040 GPIO1 -> S3JTAG GPIO6`
- `RP2040 GPIO3 -> RP2040 GPIO4`
- `RP2040 GPIO16 -> RP2040 GPIO17`
- 以及 `SWDIO / SWCLK / GND`

这组固定 wiring 已用于 formal full-suite live validation，后续 Stage 2 资产不应再漂移回旧的 `GPIO16 -> TARGETIN` 契约。

| 测试名 | 作用 | 接线要求 | 状态 |
|--------|------|----------|------|
| `test_gpio_level_low` | TARGETIN steady-low | `GPIO18 -> TARGETIN` | 已验证 |
| `test_gpio_level_high` | TARGETIN steady-high | `GPIO18 -> TARGETIN` | 已验证 |
| `test_gpio_signature_100hz` | TARGETIN low-frequency toggle | `GPIO18 -> TARGETIN` | 已验证 |
| `test_gpio_signature_1khz` | TARGETIN 1 kHz toggle | `GPIO18 -> TARGETIN` | 已验证 |
| `test_pwm_capture_with_s3jtag` | PWM 输出经 TARGETIN 验证 | `GPIO18 -> TARGETIN` | 已验证 |
| `test_gpio_interrupt_loopback_with_s3jtag` | 本地 GPIO 中断回环 | `GPIO16 -> GPIO17` | 已验证 |
| `test_uart_rxd_detect_with_s3jtag` | UART RXD 原始跳变检测 | `GPIO0 -> GPIO7` | 已验证 |
| `test_uart_banner` | Web UART bridge 验证 | `GPIO0 -> GPIO7`, `GPIO1 -> GPIO6` | 已验证 |
| `test_spi_loopback_with_s3jtag` | SPI MOSI/MISO 本地回环并经 UART 报告 | `GPIO3 -> GPIO4`，并保留 UART 线 | 已验证 |

#### 建议新增的 Stage 2 feature tests

如果 bench 和 instrument path 允许，建议后续增加：

| 候选测试名 | 作用 | 可行性判断 |
|------------|------|------------|
| `test_spi_banner_with_s3jtag` | RP2040 SPI 功能 exercised 后通过 Web UART 报告结果 | **可行**。现有 `rp2040_pico_spi` 固件可作为起点，但需改造成 S3JTAG 版 asset/plan |
| `test_i2c_banner_with_s3jtag` | RP2040 I2C 功能 exercised 后通过 Web UART 报告结果 | **可行**。现有 `rp2040_pico_i2c` 固件可作为起点，但需定义具体 loopback/peer contract |
| `test_adc_internal_temp_with_s3jtag` | 读取 RP2040 内部温度传感器后通过 Web UART 报告值 | **更适合 Stage 1**，因为无需额外接线 |
| `test_adc_external_with_s3jtag` | 外部模拟输入 ADC 验证 | **条件可行**，但必须先定义外部模拟刺激 contract；现有 `rp2040_adc_banner.json` 还不够正式 |
| `test_pwm_capture_with_s3jtag` | PWM 输出经 TARGETIN 或其他数字输入验证 | **可行**，如果用单线数字采样；若只靠板载 LED，则更像 Stage 1 self-test |

用户提出的 `AD / SPI / PWD / I2C` 中：
- `AD`：分成两类
  - 内部温度 ADC：更适合 Stage 1
  - 外部模拟输入 ADC：属于 Stage 2
- `SPI`：适合 Stage 2
- `I2C`：适合 Stage 2
- `PWD`：如果你的意思是 `PWM`，那它取决于验证方式
  - 板载 LED / 内部逻辑：Stage 1
  - 需要外部连线测 PWM 波形：Stage 2

### 4.4 Rule D / Full Suite

建议最终提供两层 convenience：

1. `full pack`
- runner 逐个执行 Stage 0 + Stage 2 当前已验证 truth-layer tests
- Stage 1 在 no-wire self-tests 落地后再并入

2. 可选 combined firmware `test_full_suite`
- 只有在确实需要更快板检、并且每个 sub-test 已单独稳定后才考虑
- 当前不是必要前置条件

---

## 5. 建议的目标文件布局

### 5.1 truth-layer firmware

建议未来形态：

```text
assets_golden/duts/rp2040_pico/
  hello_s3jtag/
  minimal_runtime_mailbox_s3jtag/
  internal_temp_s3jtag/
  pwm_led_s3jtag/
  timer_mailbox_s3jtag/
  flash_read_s3jtag/
  gpio_level_low_s3jtag/
  gpio_level_high_s3jtag/
  gpio_signature_100hz_s3jtag/
  gpio_signature_s3jtag/
  uart_banner_s3jtag/
  spi_banner_s3jtag/
  i2c_banner_s3jtag/
  adc_external_s3jtag/
  full_suite_s3jtag/          # 可选，后置
```

### 5.2 test plans

建议未来形态：

```text
tests/plans/rp2040_pico_rule_b/
  hello.json
  test_minimal_runtime_mailbox.json
  test_internal_temp.json
  test_pwm_led.json
  test_timer_mailbox.json
  test_flash_read.json
  test_gpio_level_low.json
  test_gpio_level_high.json
  test_gpio_signature_100hz.json
  test_gpio_signature_1khz.json
  test_uart_banner.json
  test_spi_banner.json
  test_i2c_banner.json
  test_adc_external.json
  test_full_suite.json        # 可选，后置
```

### 5.3 packs

建议最终至少保留：
- `packs/rp2040_s3jtag_stage0.json`
- `packs/rp2040_s3jtag_stage1.json`
- `packs/rp2040_s3jtag_stage2.json`
- `packs/rp2040_s3jtag_full.json`

当前正确映射应为：
- Stage 0:
  - `minimal_runtime_mailbox_s3jtag`（当前 hello-equivalent）
- Stage 1:
  - `minimal_runtime_mailbox_s3jtag`
  - `internal_temp_mailbox_s3jtag`
  - `timer_mailbox_s3jtag`
- Stage 2:
  - TARGETIN low/high/100Hz/1kHz（统一使用 `GPIO18 -> TARGETIN`）
  - `pwm_capture_with_s3jtag`
  - `gpio_interrupt_loopback_with_s3jtag`
  - `uart_rxd_detect_with_s3jtag`
  - `uart_banner_with_s3jtag`
  - `spi_loopback_with_s3jtag`
- Full:
  - 当前已验证的 Stage 0 + Stage 1 + Stage 2 truth-layer tests

固定 full-suite wiring 说明：
- `RP2040 GPIO18 -> S3JTAG GPIO15 / TARGETIN`
- `RP2040 GPIO0 -> S3JTAG GPIO7`
- `RP2040 GPIO1 -> S3JTAG GPIO6`
- `RP2040 GPIO3 -> RP2040 GPIO4`
- `RP2040 GPIO16 -> RP2040 GPIO17`
- 以及 `SWDIO / SWCLK / GND`

---

## 6. 当前状态与缺口分析

### 6.1 已经满足 Rule-B 精神的部分

已经满足的：
- 多个测试是独立 firmware + 独立 plan + 独立 PASS/FAIL
- 已经有 formal pack 和 closeout
- 已经验证了 truth-layer 单测，而不是只靠一个 monolithic suite
- Stage 2 里的 `TARGETIN` 和 `UART` 两条链路都已经 bench-validated

### 6.2 当前结构的真实缺口

尚缺的关键项：
1. **缺少 dedicated Stage 0 hello**
- 目前只有 `minimal_runtime_mailbox` 作为 hello-equivalent

2. **缺少真正的 Stage 1 no-wire self-tests**
- 这是当前最大的结构缺口
- 之前把 TARGETIN 测试放进 Stage 1 是不符合 Rule-C wiring 边界的

3. **缺少 RP2040 S3JTAG 版的 SPI / I2C / ADC / PWM feature tests**
- 泛用固件和计划存在，但还未适配为 S3JTAG truth-layer资产

4. **缺少 RP2040 自己的 Rule-B suite 完成报告**
- 现在有 feature closeout
- 但还没有一份统一的 Rule-B suite closeout

---

## 7. 推荐实施顺序

### Phase 1 — 修正当前阶段边界

1. Stage 0 保留 `minimal_runtime_mailbox_s3jtag` 作为当前 hello-equivalent
2. TARGETIN low/high/100Hz/1kHz 全部归入 Stage 2
3. UART banner 保持在 Stage 2

### Phase 2 — 补 Stage 1

优先建议新增：
- `test_internal_temp`
- `test_pwm_led`
- `test_timer_mailbox`

这三项最容易形成真正的 no-wire Stage 1。

### Phase 3 — 扩 Stage 2

优先建议新增：
- `test_spi_banner_with_s3jtag`
- `test_i2c_banner_with_s3jtag`
- `test_pwm_capture_with_s3jtag` 或 `test_adc_external_with_s3jtag`

其中：
- SPI / I2C 最自然，因为现有 generic firmware 已经存在
- ADC external 只有在刺激 contract 明确后才应正式化

### Phase 4 — 写 RP2040 Rule-B Suite Closeout

新增类似：
- `docs/reports/rp2040_s3jtag_rule_b_closeout_<date>.md`

### Phase 5 — 再评估 combined `test_full_suite`

建议后置。

---

## 8. 建议结论

`RP2040 + S3JTAG` 已经具备升级成 Rule-B suite 的能力基础，但必须先纠正阶段边界：
- Stage 1 只能放 no-wire tests
- 所有 TARGETIN / UART / SPI / I2C / 外部 ADC / 需跳线的 PWM 验证，都属于 Stage 2

因此当前最准确的结论是：
- RP2040 不缺 Stage 2
- RP2040 真正缺的是 Stage 1

换句话说，下一步最值得做的不是再发明更多 TARGETIN 测试，而是先补一组真正无额外接线的 RP2040 self-tests。

---

## 9A. 候选测试实现草案

下面四项是当前最值得推进的 RP2040 + S3JTAG 测试，目标是把它们收敛成真正可落地的 Rule-B truth-layer assets，而不是停留在 capability brainstorming。

### 9A.1 `rp2040_spi_loopback_with_s3jtag`

**建议阶段：** Stage 2  
**类型：** wired loopback + Web UART report

**建议接线：**
- `RP2040 GPIO2 / SPI0_SCK`：仅作为输出，不回环
- `RP2040 GPIO3 / SPI0_TX (MOSI)` → `RP2040 GPIO4 / SPI0_RX (MISO)`
- `GND` 共地

**固件建议行为：**
- 初始化 `spi0`
- 以固定节拍执行 `spi_write_read_blocking()`
- 发送固定模式，例如 `55 AA 3C C3`
- 比较回读数据是否与发送完全一致
- 通过 S3JTAG internal Web UART 打印确定性结果，例如：
  - `AEL_READY RP2040 SPI PASS rx=55aa3cc3`
  - 或 `AEL_READY RP2040 SPI FAIL rx=...`

**为什么适合优先落地：**
- 仓库已有泛用 `rp2040_pico_spi` target，可直接演进
- wiring contract 简单
- 验证的是实际 SPI data path，不只是“SPI 初始化成功”

### 9A.2 `rp2040_pwm_capture_with_s3jtag`

**建议阶段：** Stage 2  
**类型：** wired signal validation via TARGETIN

**建议接线：**
- `RP2040 PWM_OUT` → `S3JTAG TARGETIN`
- 推荐选择不与 UART 占用冲突、且便于说明的输出脚，例如 `GPIO16` 或 `GPIO18`
- `GND` 共地

**固件建议行为：**
- 使用 RP2040 PWM 外设输出固定参数波形
- 首选 contract：`1 kHz`, `50% duty`
- 可后续扩展 second profile，例如 `100 Hz`, `25% duty`

**AEL 验证建议：**
- 复用现有 TARGETIN signal-check path
- 明确验：
  - `min_freq_hz / max_freq_hz`
  - `duty_min / duty_max`
- PASS 以外部观测为准，不依赖 DUT 自报

**价值：**
- 直接复用已 bench-validated 的 TARGETIN 路径
- 从“generic gpio signature”升级为真正的 PWM feature test

### 9A.3 `rp2040_gpio_interrupt_loopback_with_s3jtag`

**建议阶段：** Stage 2  
**类型：** wired functional loopback

**建议接线：**
- `RP2040 GPIO16` (output pulse source) → `RP2040 GPIO17` (IRQ input)
- `GND` 共地

**固件建议行为：**
- `GPIO16` 输出固定数量脉冲，例如 `100` 个 rising edges
- `GPIO17` 配置为 rising-edge IRQ
- IRQ handler 计数
- 结束时检查 `irq_count == pulse_count`
- 通过 mailbox 或 Web UART 输出：
  - `AEL_READY RP2040 GPIO_IRQ PASS count=100`

**为什么有价值：**
- 接线简单
- 结果强约束、稳定、易调试
- 比纯外部信号观察更接近真实外设/中断功能验证

### 9A.4 `rp2040_internal_temp_with_s3jtag`

**建议阶段：** Stage 1  
**类型：** no-wire self-test

**建议 contract：**
- 使用 RP2040 内部温度传感器 ADC 通道
- 连续读取多次，例如 `8` 到 `16` 次
- 验证：
  - 采样非全零
  - 非满量程饱和
  - 多次采样落在合理窗口
- 通过 mailbox 或 Web UART 输出：
  - `AEL_READY RP2040 TEMP sample=...`

**为什么重要：**
- 它不依赖任何额外接线
- 能补上当前 RP2040 Rule-B 最大结构缺口：真正的 Stage 1 no-wire self-test

### 9A.5 推荐优先级

建议实现顺序：
1. `rp2040_spi_loopback_with_s3jtag`
2. `rp2040_pwm_capture_with_s3jtag`
3. `rp2040_gpio_interrupt_loopback_with_s3jtag`
4. `rp2040_internal_temp_with_s3jtag`

原因：
- 前三项能最快扩充高价值的 Stage 2 wired feature coverage
- `internal_temp` 虽然实现简单，但主要解决的是 Rule-B Stage 1 结构缺口

## 9. 下一步建议（可直接执行）

建议下一轮按以下顺序做：

1. 把 `TARGETIN` low/high/100Hz/1kHz 全部视为 Stage 2 truth-layer tests
2. 补 Stage 1 的三个 no-wire 候选：
   - `internal_temp`
   - `pwm_led`
   - `timer_mailbox`
3. 选一项最容易的 Stage 2 feature 扩展：
   - `spi_banner_with_s3jtag`
4. 再做：
   - `i2c_banner_with_s3jtag`
   - `adc_external_with_s3jtag` 或 `pwm_capture_with_s3jtag`
5. 最后写 `RP2040 Rule-B Suite 完成报告`
