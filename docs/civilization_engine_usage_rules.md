# AEL Civilization Engine — 使用规则与执行规范（V1）

**Date:** 2026-03-23
**Status:** Active — enforced from this session onward

---

## 背景：为什么需要强制规则

没有强制规则，Civilization Engine 会退化为被动文档库：
- 有经验不查 → 重复探索
- 查了不用 → 经验死锁
- 没有分级 → 重要经验和无用信息混在一起
- 没有 audit → 无法验证规则是否在执行

本文件定义可执行的操作规范，而不是原则声明。

---

## 与用户原始规则的差异说明

用户规定了 6 条规则。以下是基于实际系统状态提出的调整：

| 用户规则 | 调整 | 原因 |
|---------|------|------|
| 规则1: 必须先查询 | 新增**查询词映射表** | EE 是 keyword-based，没有映射表则"必须查询"无法操作化 |
| 规则4: 经验分级 | 映射到 EE `scope` 字段 | 系统已有 scope 字段，避免引入新概念 |
| 规则5: 高优先级提升 | 用 `[HIGH_PRIORITY]` + `scope='pattern'` + `confidence≥0.8` | EE 无 priority 字段，用 raw text 标记 + confidence 值代替 |
| 规则6: audit 报告 | 定义标准格式 | 原规则未规定格式，需要结构化才能验证执行 |

---

## 规则 1 — 任务开始前强制查询

**触发条件（满足任一）：**
- 新板 bring-up（任何芯片）
- 新 firmware 实验或 test suite
- 新接线方案
- 已有板的新外设测试

**查询步骤：**

```python
import sys
sys.path.insert(0, '/nvme1t/work/codex/experience_engine')
from api import ExperienceAPI

# 1. 查已有成功记录
hits = ExperienceAPI.query(keyword=board_id, domain='engineering', outcome='success')

# 2. 查跨板高优先级 pattern
patterns = ExperienceAPI.query(keyword='HIGH_PRIORITY', domain='engineering')

# 3. 查 avoid paths（已知陷阱）
avoids = ExperienceAPI.query(keyword=board_id, domain='engineering', avoid=True)
```

**查询词映射表：**

| 任务类型 | 首要关键词 | 补充关键词 |
|---------|-----------|-----------|
| ESP32 任何新板 bring-up | `HIGH_PRIORITY` | `<board_id>`, `esp32` |
| PCNT / pulse loopback | `pcnt` | `loopback`, `<board_id>` |
| LEDC / PWM | `ledc` | `pwm`, `<board_id>` |
| Wi-Fi scan | `wifi` | `<board_id>` |
| BLE scan / advertise | `ble` | `nimble`, `<board_id>` |
| NVS read/write | `nvs` | `<board_id>` |
| Light sleep / wakeup | `sleep` | `wakeup`, `<board_id>` |
| Partition / sdkconfig | `sdkconfig` | `partition` |
| STM32 任何测试 | `<board_id>` | `stm32`, 外设名 |

---

## 规则 2 — 有 Pattern 时默认复用

若命中 `[HIGH_PRIORITY]` 或 `scope='pattern'` 条目：
1. 优先应用该 pattern
2. 只替换 board-specific 参数
3. 不得直接重新探索
4. 若决定不复用，必须明确说明理由（技术不兼容 / scope 不符）

---

## 规则 3 — 任务结束后分级记录

### 分级标准

| 级别 | 条件 | EE scope | raw 标记 |
|------|------|---------|---------|
| 局部一次性 | 单板单测试，不可迁移 | `task` | 无 |
| 可复用 skill | 同芯片族可复用 | `board_family` | `[skill]` |
| 跨板 pattern | ≥2 板验证，可迁移 | `pattern` | `[HIGH_PRIORITY] [skill] [pattern]` |

### 记录模板

```python
# 成功记录
exp_id = ExperienceAPI.add(
    raw=f'[{board_id}] {test_name}: success — ...',
    domain='engineering',
    intent=f'verify {board_id} with {test_name}',
    source='<script path>',
    actions=['stage:build', 'stage:flash', 'stage:uart_read', 'stage:parse'],
    outcome='success',
    scope='board_family',  # 或 'task' / 'pattern'
)

# 同步到 run_index
from ael.civilization import run_index
run_index.record_success(board_id, test_name, exp_id)
```

### Avoid 记录模板（已知陷阱）

```python
exp_id = ExperienceAPI.add(
    raw=f'[{board_id}] [avoid] trigger: <描述> | failure: <现象> | fix: <修复>',
    domain='engineering',
    outcome='failed',
    scope='board_family',
)
```

### Debug 教训记录规则（必须遵守）

任务中发生过 debug（crash / build fail / test fail 后修复）时，**每一个独立的 bug 必须单独一条 EE entry**。禁止将多个 bug 合并进一段描述。

**强制检查清单：**

1. **逐条记录**：N 个不同根因 → N 条独立 `ExperienceAPI.add()` 调用
2. **intent 可搜索**：intent 字段必须描述"如何避免"，不是"发生了什么"
   - ✗ 差：`intent='debug esp32c5 gpio crash'`
   - ✓ 好：`intent='avoid Store access fault from IRAM_ATTR variable with PMP_IDRAM_SPLIT'`
3. **raw 包含技术关键词**：症状、触发条件、具体 fix 要写进 raw，便于关键词查询
4. **scope 按可迁移性判断**：
   - 可迁移到同芯片族 → `board_family`
   - 可迁移到跨芯片平台 → `pattern`，raw 加 `[HIGH_PRIORITY]`
5. **不得用 `record_run()` 代替教训记录**：`record_run()` 只记录 pass/fail 结果，不承载 debug 知识

**Debug 教训模板：**

```python
# 每个 bug 单独一条，禁止合并
exp_id = ExperienceAPI.add(
    raw=(
        '[{board_id}] [avoid] '
        'trigger: <触发条件，精确到 API/配置> | '
        'symptom: <现象，包括 MCAUSE/地址等关键信息> | '
        'root_cause: <根因> | '
        'fix: <具体修法> | '
        'confirmed: <芯片型号 + IDF版本>'
    ),
    domain='engineering',
    intent='avoid <问题类型> on <芯片> when <场景>',
    outcome='success',     # 表示问题已修复
    scope='board_family',  # 或 'pattern' + [HIGH_PRIORITY]
)
```

---

## 规则 4 — 高优先级资产提升条件

满足全部条件时提升：

| 条件 | 检验方法 |
|------|---------|
| 多次复用成功（≥2 个不同 board/任务） | run_index success_count ≥ 2 across different boards |
| 显著提速（≥10×）或显著降低试错 | 有对照数据（如 5h→5min） |
| 具有迁移性 | pattern 在新 board 上 first-run PASS |

提升操作：
```python
# 1. 创建 scope='pattern' 记录，raw 加 [HIGH_PRIORITY]
exp_id = ExperienceAPI.add(raw='[HIGH_PRIORITY] [skill] [pattern] ...', scope='pattern', ...)

# 2. 正向反馈提升 confidence
ExperienceAPI.feedback(exp_id, 'correct', 'success')
ExperienceAPI.feedback(exp_id, 'correct', 'success')

# 3. 在 docs/skills/ 创建对应 skill 文档
# 4. 在 CLAUDE.md 高优先级资产表中登记
```

---

## 规则 5 — 报告必须包含 CE Audit

### 标准 Audit 格式

```markdown
## Civilization Engine Usage Audit

| 项目 | 内容 |
|------|------|
| 查询关键词 | `HIGH_PRIORITY`, `<board_id>`, ... |
| 命中记录 | `<exp_id>` — <摘要> |
| 是否复用 | 是 / 否（原因：...） |
| 本次新增 | `<exp_id>` scope=<level> |
| 资产升级 | `<exp_id>` → scope='pattern' / 无 |
```

---

## 现有高优先级资产清单

### scope='pattern' — 跨板可复用方法论

| 资产名 | EE ID | 适用范围 | 验证记录 |
|-------|-------|---------|---------|
| Minimal-Instrument Board Bring-up Pattern | `933fc74a` | ESP32 / RISC-V 双USB开发板 | C6(1次) + C5(1次) |

### scope='pattern' — 跨板高优先级

| 资产名 | EE ID | 适用范围 |
|-------|-------|---------|
| Minimal-Instrument Board Bring-up Pattern | `933fc74a` | ESP32 / RISC-V 双USB开发板 |
| **IRAM_ATTR variable + PMP_IDRAM_SPLIT = Store fault** | `d26958c3` | ESP32-C5 及所有 PMP IDRAM split 目标 |

### scope='board_family' — 单芯片族可复用

| 资产 | EE ID | board_id / 说明 |
|------|-------|----------------|
| esp32c6_suite_ext success | `39b99875` | esp32c6_devkit_dual_usb |
| esp32c5_suite_ext success | `2ee2d4f1` | esp32c5_devkit_dual_usb |
| LEDC 10-bit freq/2 on C6 (avoid) | `06fca084` | esp32c6_devkit_dual_usb |
| sdkconfig.defaults override (avoid) | `af1b33a5` | esp32_dual_usb |
| gpio_install_isr_service 须在 WiFi/BLE 之前 | `dbdf36fb` | esp32c5_devkit_dual_usb |
| ESP_MAIN_TASK_STACK_SIZE=8192（11驱动套件）| `73f41c63` | esp32c5_devkit_dual_usb |
| GPIO interrupt 测试须在 PCNT 之前（共享 pin）| `92297155` | esp32c5_devkit_dual_usb |

---

## 关联文件

| 文件 | 用途 |
|------|------|
| `CLAUDE.md` | Claude Code 强制行为规范（机器可读） |
| `docs/esp32_bringup_civilization_pattern_v1.md` | 完整 pattern 描述 |
| `docs/skills/minimal_instrument_bringup_skill.md` | skill 定义文档 |
| `experiments/templates/esp32_minimal_bringup_template.py` | 参数化实验模板 |
| `ael/patterns/loopback/pcnt_loopback.py` | PCNT pattern 代码模块 |
| `ael/civilization/engine.py` | CE AEL wrapper |
| `ael/civilization/run_index.py` | 运行统计索引 |
