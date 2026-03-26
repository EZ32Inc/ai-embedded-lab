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

当前状态更像：
- 若干 truth-like 单测试计划已存在
- 若干 pack 已存在（smoke / standard / uart）
- 已有 closeout 文档
- 但尚未形成明确的 `Stage 0 / Stage 1 / Stage 2 / Full` 套件结构
- 尚缺一份 RP2040 自己的 Rule-B suite 说明和最终完成报告

本设计草案的目的，是把现有 RP2040 资产映射为 Rule-B 架构，并明确缺口和下一步实现顺序。

---

## 2. Rule-B 目标结构

### 2.1 架构分层

建议的 RP2040 Rule-B 套件结构：

```text
Stage 0  ─ hello                          (最小 bring-up，无复杂集成依赖)
Stage 1  ─ minimal_runtime_mailbox / gpio_level_low / gpio_level_high / gpio_signature_100hz / gpio_signature_1khz
Stage 2  ─ uart_banner                    (以及未来的 spi / i2c / integration tests)
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

这里的可观测信号不一定必须是传统 UART console。
对 `RP2040 + S3JTAG` 来说，更合理的是：
- mailbox/minimal runtime proof，或
- 一个极简 UART hello，或
- 一个极简 TARGETIN 心跳

但它必须满足 Rule A 的精神：
- 无复杂依赖
- 无额外诊断歧义
- 先证明控制性和可观察性成立

#### Rule B — One Test, One Program
每个测试必须独立：
- 单独 firmware asset
- 单独 test plan
- 单独 PASS/FAIL
- 能单独 rerun / debug

#### Rule C — Stage by Dependency
测试要按依赖分层：
- 先最小 bring-up
- 再较简单的 no-extra-wire / single-extra-wire 功能验证
- 再真正的 integration tests

#### Rule D — Optional Full Suite
在 truth layer 稳定后，允许引入：
- `full pack`，由 runner 顺序编排全部单测
- 或 combined firmware `test_full_suite`

但 full suite 必须是 convenience layer，不得替代 truth layer。

---

## 3. 当前 RP2040 资产盘点

### 3.1 已有 test plans

当前已存在：
- `tests/plans/rp2040_minimal_runtime_mailbox_s3jtag.json`
- `tests/plans/rp2040_gpio_level_low_with_s3jtag.json`
- `tests/plans/rp2040_gpio_level_high_with_s3jtag.json`
- `tests/plans/rp2040_gpio_signature_100hz_with_s3jtag.json`
- `tests/plans/rp2040_gpio_signature_with_s3jtag.json`
- `tests/plans/rp2040_uart_banner_with_s3jtag.json`

另有非 S3JTAG 泛用计划：
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

### 3.3 已有 golden firmware assets

当前已存在：
- `assets_golden/duts/rp2040_pico/minimal_runtime_mailbox_s3jtag/`
- `assets_golden/duts/rp2040_pico/gpio_level_low_s3jtag/`
- `assets_golden/duts/rp2040_pico/gpio_level_high_s3jtag/`
- `assets_golden/duts/rp2040_pico/gpio_signature_100hz_s3jtag/`
- `assets_golden/duts/rp2040_pico/gpio_signature_s3jtag/`
- `assets_golden/duts/rp2040_pico/uart_banner_s3jtag/`

### 3.4 已完成的正式 closeout

当前已存在：
- `docs/rp2040_s3jtag_gpio_validation_closeout_2026-03-26.md`
- `docs/rp2040_s3jtag_standard_suite_closeout_2026-03-26.md`
- `docs/rp2040_s3jtag_uart_validation_closeout_2026-03-26.md`
- `docs/skills/rp2040_s3jtag_signal_validation_skill_2026-03-26.md`
- `docs/skills/rp2040_s3jtag_uart_validation_skill_2026-03-26.md`

结论：
- truth-layer 资产已经有一大半
- 现阶段缺的不是“从零做测试”，而是“把已有测试组织成 Rule-B suite”

---

## 4. 建议的 RP2040 Rule-B 测试清单

### 4.1 Stage 0

| 测试名 | 作用 | 建议观测方式 | 状态 |
|--------|------|--------------|------|
| `hello` | 最小 bring-up，证明 SWD flash + deterministic startup | mailbox 或最小 UART banner，择一 | **缺失** |

建议：
- 不要让 `hello` 直接变成复杂 integration test
- 最好避免依赖太多额外接线
- 优先考虑：
  - `hello_mailbox_s3jtag`，或
  - `hello_uart_s3jtag`（如果 UART 已证明足够稳）

### 4.2 Stage 1

| 测试名 | 作用 | 设计意图 | 状态 |
|--------|------|----------|------|
| `test_minimal_runtime_mailbox` | 最小 runtime gate | 最接近 Rule A/基础真相层 | 已有 |
| `test_gpio_level_low` | TARGETIN steady-low 验证 | 单线数字输入低电平 | 已有 |
| `test_gpio_level_high` | TARGETIN steady-high 验证 | 单线数字输入高电平 | 已有 |
| `test_gpio_signature_100hz` | TARGETIN 低频 toggle 验证 | 较低频数字活动 | 已有 |
| `test_gpio_signature_1khz` | TARGETIN 1 kHz toggle 验证 | 更强的 toggle 验证 | 已有 |

说明：
- 这些测试已经基本构成一个很不错的 Stage 1 truth layer
- 和 ESP32 Rule-B 的 Stage 1 不同，RP2040 这里的 Stage 1 更偏向“instrument-path validation”而不是片上外设自测
- 这是合理的，因为 `S3JTAG` 是这个 board profile 的核心

### 4.3 Stage 2

| 测试名 | 作用 | 设计意图 | 状态 |
|--------|------|----------|------|
| `test_uart_banner` | Web UART bridge 验证 | 证明 `SWD + UART bridge` 一体链路 | 已有 |
| `test_spi_banner` | SPI integration | 未来可接入 | 仅泛用计划存在 |
| `test_i2c_banner` | I2C integration | 未来可接入 | 仅泛用计划存在 |
| `test_adc_banner` | ADC / analog-ish path | 未来可接入 | 仅泛用计划存在 |

说明：
- 目前 RP2040 over S3JTAG 的 Stage 2 只正式完成了 UART
- SPI/I2C/ADC 是否进入 Rule-B suite，取决于后续 bench 和 instrument path 是否要覆盖这些能力
- 如果当前目标只做 S3JTAG validated suite，那么可以先只放 `uart_banner`

### 4.4 Rule D / Full Suite

建议最终提供两层 convenience：

1. `full pack`
- runner 逐个执行 Stage 0 + Stage 1 + Stage 2
- 这是最接近 Rule D 推荐路径的做法
- truth layer 保持不变

2. 可选 combined firmware `test_full_suite`
- 只有在确实需要更快板检、并且每个 sub-test 已单独稳定后才考虑
- 当前不是必要前置条件

建议优先级：
- 先做 `full pack`
- `test_full_suite` 可以后做

---

## 5. 建议的目标文件布局

### 5.1 truth-layer firmware

建议未来形态：

```text
assets_golden/duts/rp2040_pico/
  hello_s3jtag/
  minimal_runtime_mailbox_s3jtag/
  gpio_level_low_s3jtag/
  gpio_level_high_s3jtag/
  gpio_signature_100hz_s3jtag/
  gpio_signature_s3jtag/
  uart_banner_s3jtag/
  full_suite_s3jtag/          # 可选，后置
```

### 5.2 test plans

建议未来形态：

```text
tests/plans/rp2040_pico_rule_b/
  hello.json
  test_minimal_runtime_mailbox.json
  test_gpio_level_low.json
  test_gpio_level_high.json
  test_gpio_signature_100hz.json
  test_gpio_signature_1khz.json
  test_uart_banner.json
  test_full_suite.json        # 可选，后置
```

如果不想新开目录，也可以先沿用现有 plans，但长期更建议像 Rule-B 报告那样按 board family 归档。

### 5.3 packs

建议最终至少新增：
- `packs/rp2040_s3jtag_stage0.json`
- `packs/rp2040_s3jtag_stage1.json`
- `packs/rp2040_s3jtag_stage2.json`
- `packs/rp2040_s3jtag_full.json`

当前 pack 到目标结构的映射：
- `smoke_rp2040_s3jtag.json` → 可作为 Stage 0/1 过渡资产
- `standard_rp2040_s3jtag.json` → 接近 Stage 1
- `uart_rp2040_s3jtag.json` → 可并入 Stage 2

但这些名字还不是标准 Rule-B stage 命名，建议后续明确重命名或新增 stage-pack 包装层。

---

## 6. 当前状态与缺口分析

### 6.1 已经满足 Rule-B 精神的部分

已经满足的：
- 多个测试是独立 firmware + 独立 plan + 独立 PASS/FAIL
- 已经有 formal pack 和 closeout
- 已经验证了 truth-layer 单测，而不是只靠一个 monolithic suite
- 已经有 smoke / standard / uart 三种组合层

### 6.2 尚未完全满足的部分

尚缺的关键项：
1. **缺少明确的 Stage 0 hello**
- 这是 Rule A 的核心要求
- 现在最接近的是 `minimal_runtime_mailbox`，但它应不应该直接承担 `hello` 角色，需要明确

2. **缺少标准 Rule-C stage packs**
- 当前是 `smoke / standard / uart`
- Rule-B 报告参考里是 `stage0 / stage1 / stage2 / full`

3. **缺少 RP2040 自己的 Rule-B suite 定义文档 / 完成报告**
- 现在有 feature closeout
- 但还没有像 `esp32c3_devkit_rule_b_closeout_2026-03-26.md` 那样的统一 suite 报告

4. **缺少明确的 Rule D convenience layer 说明**
- 当前可以用 full pack 解决
- combined firmware `test_full_suite` 仍是可选后续项

---

## 7. 推荐实施顺序

### Phase 1 — 定义 Stage 0

建议先做：
- 明确 `minimal_runtime_mailbox_s3jtag` 是否可升级为 Rule-A `hello`

如果不合适，则新增：
- `hello_s3jtag`
- 最小要求：
  - SWD 可烧录
  - 启动即输出确定性信号
  - 无复杂 wiring 依赖

### Phase 2 — 生成标准 stage packs

基于现有 truth-layer 测试，新增：
- `rp2040_s3jtag_stage0.json`
- `rp2040_s3jtag_stage1.json`
- `rp2040_s3jtag_stage2.json`
- `rp2040_s3jtag_full.json`

推荐映射：
- Stage 0:
  - `hello` 或 `minimal_runtime_mailbox`
- Stage 1:
  - mailbox
  - gpio low
  - gpio high
  - gpio 100 Hz
  - gpio 1 kHz
- Stage 2:
  - uart banner
- Full:
  - Stage 0 + Stage 1 + Stage 2 全部

### Phase 3 — 写 RP2040 Rule-B Suite Closeout

新增类似：
- `docs/reports/rp2040_s3jtag_rule_b_closeout_<date>.md`

内容应仿照 C3/S3 Rule-B 报告，包括：
- 工作概述
- 测试套件结构
- Stage 0/1/2/Rule D 分层
- 接线要求
- 关键设计决策
- 遇到的问题与解决过程
- 最终测试结果
- CE/skills/经验总结
- 文件变更清单

### Phase 4 — 评估是否需要 combined firmware `test_full_suite`

建议后置。

原因：
- 当前 `full pack` 已经足够满足 Rule D 的推荐模型
- combined firmware 只有在你明确需要更快量产板检或本地一次烧录全跑时才值得做

---

## 8. 建议结论

`RP2040 + S3JTAG` 已经具备升级成 Rule-B suite 的条件。

最务实的路径不是重做现有测试，而是：
- 承认现有 truth-layer 测试已经存在
- 补齐 `Stage 0`
- 用 Rule-C 的方式把已有 truth-layer 测试重组为 `stage0 / stage1 / stage2 / full`
- 最后出一份统一的 Rule-B suite closeout

换句话说，RP2040 当前距离 Rule-B 完成态，不差“能力”，差的是“结构”。

这也是与 `docs/reports/*_rule_b_closeout_*.md` 对齐时最重要的判断：
- 目标不是再多做几个功能点
- 目标是把已有能力提升为标准化、分层、可复用、可汇报的 Rule-B Golden Suite

---

## 9. 下一步建议（可直接执行）

建议下一轮按以下顺序做：

1. 明确 `minimal_runtime_mailbox_s3jtag` 是否直接担任 Stage 0 `hello`
2. 新增 4 个标准 Rule-B pack：
   - `rp2040_s3jtag_stage0.json`
   - `rp2040_s3jtag_stage1.json`
   - `rp2040_s3jtag_stage2.json`
   - `rp2040_s3jtag_full.json`
3. 跑完整 stage packs live validation
4. 写 `RP2040 Rule-B Suite 完成报告`
5. 如有量产/板检需求，再评估 `test_full_suite` combined firmware
