# AEL Project — Claude Code Instructions

## Civilization Engine: 强制入口规则

以下规则对所有涉及 board bring-up / validation / experiment 的任务强制执行。

---

### 规则 1 — 任务开始前必须查询 Civilization Engine

触发条件（满足任一即查询）：
- 新板 bring-up（任何芯片）
- 新 firmware 实验 / test suite
- 新接线方案
- 已有板的新测试

**查询步骤**（按顺序执行）：

```python
# Step 1: 按 board_id 查已有成功记录
results = ExperienceAPI.query(keyword=board_id, domain='engineering', outcome='success')

# Step 2: 查是否有跨板 pattern（HIGH_PRIORITY）
patterns = ExperienceAPI.query(keyword='HIGH_PRIORITY', domain='engineering')

# Step 3: 查 avoid paths（已知陷阱）
avoid = ExperienceAPI.query(keyword=board_id, domain='engineering', avoid=True)
```

**关键词映射表**（任务类型 → 查询关键词）：

| 任务类型 | 首要查询词 | 补充查询词 |
|---------|----------|-----------|
| ESP32 新板 bring-up | `HIGH_PRIORITY` | `board_id`, `esp32`, `bringup` |
| PCNT / loopback 测试 | `pcnt` | `loopback`, `board_id` |
| PWM / LEDC 测试 | `ledc` | `pwm`, `board_id` |
| Wi-Fi 测试 | `wifi` | `board_id` |
| BLE 测试 | `ble` | `nimble`, `board_id` |
| 分区表 / sdkconfig | `sdkconfig` | `partition`, `board_id` |
| STM32 GPIO / UART | `board_id` | `stm32`, `loopback` |

---

### 规则 2 — 有 pattern 时默认复用

若查到 `[HIGH_PRIORITY]` 或 `scope=pattern` 的记录：
- **必须**先应用该 pattern，不得直接重新探索
- 仅替换 board-specific 参数（serial numbers、GPIO、IDF_TARGET）
- 若决定不复用，必须在响应中说明原因

---

### 规则 3 — 任务结束后分级记录

```python
# 局部一次性经验 → scope='task'
ExperienceAPI.add(..., scope='task')

# 可复用 skill（单板族） → scope='board_family'
ExperienceAPI.add(..., scope='board_family')

# 跨板/跨任务方法、pattern → scope='pattern'，raw 加 [HIGH_PRIORITY]
ExperienceAPI.add(..., scope='pattern')
```

**同时更新 run_index**：
```python
from ael.civilization import run_index
run_index.record_success(board_id, test_name, exp_id)
```

---

### 规则 4 — 高优先级资产提升条件

满足以下全部条件时，必须提升为 `scope='pattern'` + `[HIGH_PRIORITY]`：
- 多次复用成功（≥2 个不同 board/任务）
- 显著提速（≥10×）或显著降低试错
- 具有迁移性（可应用于未来不同 board）

---

### 规则 5 — 报告必须包含 CE Audit

每次任务结束的报告/总结必须包含：

```
## Civilization Engine Usage Audit
查询了什么：<keyword list>
命中了什么：<exp_id list or "无">
是否复用：<是/否，原因>
新增记录：<exp_id list or "无">
升级资产：<scope='pattern' 条目 or "无">
```

---

## 现有高优先级资产

| 资产 | EE ID | 适用范围 | confidence |
|------|-------|---------|-----------|
| Minimal-Instrument Board Bring-up Pattern | `933fc74a` | ESP32 / RISC-V 双USB开发板 | 0.5→提升中 |

---

## 系统路径

```python
# Experience Engine
sys.path.insert(0, '/nvme1t/work/codex/experience_engine')
from api import ExperienceAPI

# Civilization Engine (AEL wrapper)
from ael.civilization.engine import CivilizationEngine

# PCNT loopback pattern
from ael.patterns.loopback.pcnt_loopback import pcnt_loopback_c_snippet, parse_pcnt_result

# Experiment template
# experiments/templates/esp32_minimal_bringup_template.py
```
