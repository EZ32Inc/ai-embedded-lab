# Postmortem: STM32G431CBU6 Bring-Up Milestone

## Status
Final — milestone closed 2026-03-16. smoke_stm32g431 9/9 PASS confirmed on hardware.

---

## 1. 任务总结

**目标：** 完成 STM32G431CBU6 的完整 bring-up，覆盖 8 个外设功能测试，并在此过程中建立可复用的调试基础设施。

**最终状态：**
- `smoke_stm32g431` 共 9 个测试，9/9 PASS
- `STM32G431CBU6` promoted to `verified`
- 新增第 9 个程序 `minimal_runtime_mailbox`，作为 Step 0 debug-path gate
- `check.mailbox_verify` 作为正式 pipeline stage 完成集成
- 所有 8 个外设固件已集成 `ael_mailbox.h` 共享邮箱头

**状态变化时间线：**
- 初始状态：6/8 PASS（SPI、ADC 失败）
- SPI 修复后：7/8
- ADC 修复后：8/8 PASS，board promoted to verified
- 邮箱 PoC 验证（PASS 和 FAIL variant 均在硬件上确认）
- 8 个固件集成邮箱
- 第 9 个程序 `minimal_runtime_mailbox` 创建并进入 pack
- `check.mailbox_verify` pipeline stage 集成
- 9/9 全通，里程碑关闭

---

## 2. 关键失败与修复

### 2.1 SPI — RXNE 永不置位

**Symptom:** SPI 测试失败，loopback 无法接收到字节。

**Root cause:** STM32G4 的 SPI 有 32 位 FIFO，RXNE 默认阈值是 16 位（两字节）。8 位传输时，数据进入 FIFO 后 RXNE 不会置位，导致固件永久等待。该寄存器字段 `CR2.FRXTH` 在 F1/F4 上不存在，是 G4 特有的 missing transplant。

**Exact fix:**
```c
SPI1_CR2 = (7u << 8) | (1u << 12);  /* DS=8-bit, FRXTH=1 */
SPI1_CR1 |= (1u << 6);              /* SPE — enable after CR1+CR2 */
```

**Why this is correct:** `FRXTH=1` 将 RXNE 阈值降为 8 位，每收到一字节立即置位。SPE 必须在 CR2 配置完成后单独写入，否则 FRXTH 设置被覆盖。

**Evidence:** 代码 diff 确认原始代码完全没有 CR2 写入，是直接从 F401 风格迁移的结果。

---

### 2.2 ADC — EOC 永不置位

**Symptom:** ADC 测试失败，转换永不完成。

**Root cause:** STM32G4 的 ADC 时钟必须通过 `ADC12_CCR.CKMODE` 显式选择。默认值 `CKMODE=00`（异步时钟）需要 ADC PLL，而固件没有配置 PLL。F4 风格代码中 ADC 时钟由 APB2 隐式提供，这一步骤在心智模型中是"不可见的"——重写时同样被遗漏。

**Exact fix:**
```c
#define ADC12_CCR (*(volatile uint32_t *)0x50000308u)
ADC12_CCR |= (1u << 16);  /* CKMODE=01: synchronous HCLK/1 — before ADVREGEN */
```

**Why this is correct:** `CKMODE=01` 使用同步 HCLK/1，不需要 PLL，与 HSI + 无分频器的启动配置兼容。必须在 ADVREGEN 使能前设置。

**Evidence:** 无 CubeMX 对比时，通过逐步追踪 G4 RM 的 ADC 初始化序列发现。

---

### 2.3 两种 cross-family 错误模式

这两个失败共同定义了 cross-family migration 的两种经典错误：

**Pattern 1 — Missing Transplant（SPI）：** 代码从 F401 复制，G4 特有机制（FRXTH）完全缺失，没有"复制了再忘"，而是"根本没有"。

**Pattern 2 — Implicit Assumption（ADC）：** 代码是重新写的，但 F4 的心智模型（"时钟总是通过 APB2 来的"）导致 G4 特有的必要步骤（CKMODE）在意识上不可见。

---

## 3. 新学到的规则

### 规则 1：新 family bring-up 不应默认复用旧 family 外设实现

任何外设代码从一个 STM32 family 迁移到另一个时，都应假设存在 family-specific 差异，并主动对照目标 family 的 RM 或 CubeMX 初始化序列核查。

不应假设"代码跑通了，所以没差异"——SPI 和 ADC 的失败证明，即使是看起来相同的外设，也可能有静默的行为差异。

### 规则 2：新 family 首次使用某外设时，必须检查以下三点

1. 是否有新的必要 register 或 bit field（Missing Transplant 检查）
2. 是否有新的初始化顺序要求（如 SPE 最后写）
3. 是否有新的时钟/电源依赖（如 CKMODE、ADVREGEN）

### 规则 3：debug mailbox 应是首个验证对象，不是最后一个

如果在进入外设测试之前就能确认 MCU 已启动并能写 RAM，则外设测试的失败都是外设层问题，而不是基础设施问题。这显著缩短根因定位时间。

### 规则 4：bring-up 顺序应分层

Step 0（boot gate）→ Step 1（wiring）→ Step 2（GPIO sanity）→ Step 3（外设测试），每层只在前一层确认后才进入，避免多层问题叠加。

---

## 4. 新的 Skills / Workflow 变化

### 4.1 Debug Mailbox 基础设施（新建）

- `firmware/targets/ael_mailbox.h` — 共享邮箱头，所有 G431 固件使用
- `tools/read_mailbox.py` — 命令行邮箱读取工具
- `ael/adapters/check_mailbox_verify.py` — pipeline adapter
- `check.mailbox_verify` — 已注册为正式 pipeline stage
- 测试计划中加入 `"mailbox_verify": {...}` 字段即可启用

### 4.2 Minimal Runtime Mailbox 程序（新建）

- `firmware/targets/stm32g431_minimal_runtime_mailbox/` — 第 9 个固件程序
- `tests/plans/stm32g431_minimal_runtime_mailbox.json` — 对应测试计划
- 进入 `packs/smoke_stm32g431.json` 第一位（operationally first）

### 4.3 Pipeline 的 noop 信号检查路径（新建）

`strategy_resolver.build_verify_step()` 现在能识别空 `signal_checks`，对 debug-path-only 测试返回 noop 步骤，不再尝试无意义的信号采集。

### 4.4 Cross-Family Migration Risk Spec（新建）

`docs/specs/stm32_cross_family_migration_risk_spec_v0_1.md` — 记录两种错误模式，含 LL 常量对照表和必检规则。

### 4.5 Wiring Auto-Discovery Spec（新建）

`docs/specs/bench_wiring_auto_discovery_spec_v0_1.md` — Method A/B 两种方式，Method B（频率编码并行扫描）为首选。

---

## 5. 下次应成为默认的做法

### 新 board 首次 bring-up

1. 先 flash `minimal_runtime_mailbox`，用 `read_mailbox.py` 确认 MCU 已启动
2. 确认 wiring（Method B 优先）
3. 做 pair-level GPIO sanity check
4. 再运行完整 smoke pack

不要在 Step 0 通过前尝试任何外设测试。

### 新 family 首次使用某外设

1. 对照目标 family RM 或 CubeMX 初始化序列逐步检查
2. 特别关注：新 bit field、初始化顺序、时钟/电源依赖
3. 不要默认复用其他 family 的外设代码

### Cross-family 代码迁移

在开始前明确：哪些文件是从哪个 family 复制/借鉴的，然后对每个外设逐一做 family-specific checklist。

---

## 6. 沉淀的文档列表

| 文档 | 位置 |
|---|---|
| Mailbox contract | `docs/specs/ael_mailbox_contract_v0_1.md` |
| Minimal runtime mailbox spec | `docs/specs/minimal_runtime_mailbox_spec_v0_1.md` |
| New board bring-up sequence | `docs/specs/new_board_bringup_sequence_v0_1.md` |
| Cross-family migration risk | `docs/specs/stm32_cross_family_migration_risk_spec_v0_1.md` |
| Bench wiring auto-discovery | `docs/specs/bench_wiring_auto_discovery_spec_v0_1.md` |
| Debug mailbox result reporting | `docs/specs/debug_mailbox_result_reporting_spec_v0_1.md` |
| Bringup process recording | `docs/specs/bringup_process_recording_spec_v0_1.md` |
| Task five-part closure rule | `docs/specs/task_five_part_closure_rule_v0_1.md` |
| STM32G4 peripheral init rules | `docs/skills/stm32g4_peripheral_init_rules.md` |

---

## 一句话总结

STM32G431CBU6 bring-up 从 6/8 PASS 到 9/9 PASS，不只是修了两个外设 bug，而是在过程中建立了一套分层 bring-up 方法、debug mailbox 基础设施、cross-family 迁移风险意识、和 pipeline 级别的邮箱验证能力——这些都是可以直接复用到下一块板的系统能力。
