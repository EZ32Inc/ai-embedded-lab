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
| 外部 IDF 项目 brownfield onboarding | `brownfield` | `skip_set_target`, `instrument_firmware` |
| USB CDC observe_uart 问题 | `baud` | `usb_cdc`, `native_usb`, `observe_uart` |
| 嵌入式 Web UI 按钮/WebSocket 验证 | `playwright` | `browser`, `webui`, `websocket`, `https` |

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
| **[HIGH_PRIORITY] IRAM_ATTR variable + PMP_IDRAM_SPLIT = Store fault** | `d26958c3` | ESP32-C5 / PMP IDRAM split 目标 | 0.5 |
| **[HIGH_PRIORITY] ESP32-C5 i2c_slave_receive() bug + V2 workaround** | `87240d79` | ESP32-C5 I2C slave loopback | 0.5 |
| **[HIGH_PRIORITY] observe_uart baud=null → int(None) TypeError (USB CDC)** | `da6927bd` | 所有 USB CDC 设备（ESP32-S3 native USB 等） | 0.9 |
| **[HIGH_PRIORITY] ESP32JTAG Firmware Brownfield Onboarding Pattern** | `92fd939d` | ESP32-S3 native USB instrument firmware | 0.8 |
| **[HIGH_PRIORITY] ESP32 USB Interface Classification: native-only vs dual** | `7daa8c80` | 所有 ESP32 板（Class A dual / Class B native-only） | 0.9 |
| **[HIGH_PRIORITY] Playwright Browser Automation for Embedded Web UI Testing** | `747fdb40` | 任何带 Web UI 的嵌入式设备（HTTPS + Basic Auth + WebSocket） | 0.9 |
| **[HIGH_PRIORITY] HARDWARE_CONNECT_FIRST_RULE — ask before probing** | `04486a33` | 所有需要物理 USB/instrument 连接的任务 | 0.9 |

## ESP32-C5 board_family 已知陷阱

| 问题 | EE ID | 修法 |
|------|-------|------|
| gpio_install_isr_service 须在 WiFi/BLE 之前调用 | `dbdf36fb` | app_main 最前面先调用 |
| app_main 默认栈 3584 不够用（11 drivers） | `73f41c63` | sdkconfig: ESP_MAIN_TASK_STACK_SIZE=8192 |
| GPIO interrupt 测试须在 PCNT 之前跑 | `92297155` | 共享 pin 时 PCNT 必须最后占用 |
| i2c_slave_receive() → auto-start master bug | `87240d79` | 用 V2 driver + bit-bang master 替代 |
| I2C slave V2 receive_buf_depth=32 不够用 | `975b66b9` | 用 ≥100；RINGBUF overhead 约20字节 |
| I2C slave V2 ADDRESS_MATCH stretch at >10kHz | `958116e1` | BB_HALF_US=50 (10kHz)；保证 ACK 检测 |

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
