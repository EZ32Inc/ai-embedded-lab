# Post-Flash Runtime Verification — Design Document

> **Status**: Plan (未实现)
> **适用范围**: 通过 USB-to-UART bridge 连接的 ESP32 板（Class A dual-USB / Class B native-only 均适用）
> **核心原则**: `flash success ≠ runtime ready`
> AEL 必须在每次 flash 后，通过串口确认系统已进入 expected runtime state，才能进行后续测试。

---

## 1. 现状分析与问题定位

### 1.1 当前 flash 流程（缺口所在）

```
build → flash → [假设运行正常] → 网络连接 → 测试
                    ↑ 这里没有任何验证
```

`ael/instruments/backends/esp32_jtag/actions/flash.py` 的 `run_flash()` 在 instrument 侧返回 `{"ok": true}` 后立即返回 `status: success`。之后的 workflow 直接跳转到网络测试阶段（GDB / WebAPI / WebSocket 检查），没有任何串口日志确认。

### 1.2 已有基础设施（可复用）

| 组件 | 位置 | 作用 |
|------|------|------|
| `control_reset_serial` | `ael/adapters/control_reset_serial.py` | RTS 脉冲复位板子 |
| `UsbUartBridgeTransport.wait_for()` | `ael/instruments/backends/usb_uart_bridge/transport.py` | 等待串口出现特定 pattern |
| `uart_wait_for` action | `ael/instruments/backends/usb_uart_bridge/actions/uart_wait_for.py` | 封装 wait_for |
| `failure_recovery` | `ael/failure_recovery.py` | 标准化 failure kind + recovery hint |
| `recovery_policy` | `ael/recovery_policy.py` | reset.serial 恢复策略 |

核心能力已存在，缺少的是：
1. 一个把它们串起来的 **post-flash verify 专用编排器**
2. 在 flash 完成后自动触发的 **workflow gate**
3. 一套针对 ESP32 instrument 固件的 **expected-state 判定规则**
4. **固件侧日志规范**，保证日志可机器解析

---

## 2. 目标设计

### 2.1 新增组件列表

```
ael/
  post_flash/
    __init__.py
    verifier.py          # 核心编排：捕获日志 + 状态判定 + 重试
    state_matcher.py     # expected-state 规则引擎
    recovery.py          # post-flash 专用恢复策略
    firmware_log_spec.py # 固件日志规范常量 + 解析工具
```

**修改的现有文件**：
- `ael/instruments/backends/esp32_jtag/actions/flash.py` — flash 完成后触发 verifier（可选：通过 option 开关）
- `ael/run_manager.py` — 在 `RunPaths` 增加 `post_flash_verify_log`、`post_flash_verify_json`
- instrument config YAML（如 `s3jtag_rp2040_lab.yaml`）— 增加 `post_flash_verify` 节

---

## 3. Workflow 详细设计

### 3.1 完整流程图

```
flash()
  └─ ok=True
       │
       ▼
[POST-FLASH GATE] post_flash_verify()
  │
  ├─ Step 1: 等待固件启动，打开串口（timeout: boot_timeout_s，默认 10s）
  │          如果串口无输出 → 触发 RTS 复位一次
  │
  ├─ Step 2: 捕获启动日志（capture_window_s，默认 15s）
  │
  ├─ Step 3: state_matcher 判定 expected_state
  │          ├─ PASS → 返回 verify_result(ok=True)
  │          └─ FAIL → 进入恢复流程
  │
  ├─ Step 4 (Recovery):
  │          ├─ 检查日志中是否有 panic/crash/reboot_loop
  │          ├─ 使用 control_reset_serial 复位
  │          ├─ 重新捕获日志（最多 max_recovery_attempts 次，默认 2）
  │          └─ 仍失败 → 返回 verify_result(ok=False, reason=runtime_bringup_failed)
  │
  └─ 成功确认 → 继续后续测试（网络 / JTAG / WebSocket）
     失败 → 明确报告 flash_succeeded_but_runtime_failed，终止测试
```

### 3.2 verifier.py — 接口设计

```python
class PostFlashVerifier:
    def __init__(self, cfg: PostFlashVerifyConfig): ...

    def verify(self) -> PostFlashVerifyResult:
        """
        主入口：flash 后调用，返回 ok=True/False。
        内部执行：boot 等待 → 日志捕获 → 状态判定 → 恢复重试。
        """

@dataclass
class PostFlashVerifyConfig:
    port: str                        # 串口设备，如 /dev/ttyUSB0
    baud: int = 115200
    boot_timeout_s: float = 10.0     # 等待任何串口输出的最长时间
    capture_window_s: float = 15.0   # 完整启动日志捕获窗口
    heartbeat_confirm_s: float = 5.0 # 额外等待确认有持续 heartbeat
    max_recovery_attempts: int = 2
    expected_state: str = "instrument_ready"  # 预设 profile 名称
    custom_patterns: list[str] = field(default_factory=list)  # 额外自定义 pattern
    log_path: str | None = None      # 可选：保存原始串口日志

@dataclass
class PostFlashVerifyResult:
    ok: bool
    state_reached: str               # "instrument_ready" / "boot_only" / "no_output" / "crash"
    matched_patterns: list[str]
    missing_patterns: list[str]
    raw_log_excerpt: str
    recovery_attempts: int
    elapsed_s: float
    failure_kind: str | None         # 使用 failure_recovery 中的常量
    recovery_hint: dict | None
```

---

## 4. State Matcher — 判定规则设计

### 4.1 预设 Profile

每个 profile 定义「必须命中」和「如果命中则报异常」两组 pattern。

#### Profile: `instrument_ready`（S3JTAG 及类似 instrument 固件）

```yaml
# 必须全部命中（AND 语义）
required:
  - pattern: "AEL.*board.*OK|board.*ready|instrument.*ready"
    label: board_ready
    weight: critical

  - pattern: "wifi.*connected|sta.*connected|WiFi.*connected"
    label: wifi_connected
    weight: critical

  - pattern: "ip=\\d+\\.\\d+\\.\\d+\\.\\d+|got ip:|IP Address:"
    label: ip_assigned
    weight: critical

  - pattern: "server.*ready|gdb.*ready|websocket.*ready|ws.*ready|jtag.*ready"
    label: service_ready
    weight: critical

# 可选（命中加分，但不阻断）
optional:
  - pattern: "heartbeat"
    label: heartbeat_alive
    weight: informational

# 命中即报异常（OR 语义）
forbidden:
  - pattern: "Guru Meditation|panic|assert failed|LoadStoreError|InstrFetchProhibited"
    label: firmware_panic
  - pattern: "rst:0x[0-9a-f]+.*POWERON_RESET.*rst:0x[0-9a-f]+.*POWERON_RESET"
    label: reboot_loop   # 两次以上 POWERON_RESET
  - pattern: "ets_main\\.c|boot:0x[0-9a-f]+ \\(DOWNLOAD_BOOT\\)"
    label: stuck_in_bootloader
```

#### Profile: `boot_only`（最低验证：固件至少跑起来了）

```yaml
required:
  - pattern: "cpu_start:|app_main started|I \\(\\d+\\)"
    label: esp_idf_started
    weight: critical
```

#### Profile: `custom`

只使用 `PostFlashVerifyConfig.custom_patterns`，适合非 instrument 固件。

### 4.2 判定算法

```
state_reached 判定：
  1. 任何 forbidden pattern 命中 → state="crash"，ok=False
  2. 全部 required[weight=critical] 命中 → state=profile_name，ok=True
  3. 部分命中（有 critical 未命中）→ state="partial"，ok=False
  4. 无任何输出 → state="no_output"，ok=False
```

---

## 5. 恢复策略设计

### 5.1 错误分类与处理

| 状态 | `state_reached` | 恢复动作 | 最多重试 |
|------|-----------------|----------|---------|
| 无串口输出 | `no_output` | control_reset_serial → 重新捕获 | 2 |
| 部分启动（wifi 未连接）| `partial` | 等待额外 10s → 重试匹配 | 1 |
| Crash / Panic | `crash` | control_reset_serial → 重新捕获 | 1 |
| Reboot loop | `crash` | 记录 non_recoverable，不重试 | 0 |
| 卡在 bootloader | `stuck_in_bootloader` | 手动干预（HAR） | 0 |

### 5.2 recovery.py — 接口设计

```python
def build_recovery_hint(state: str, port: str, baud: int) -> dict | None:
    """
    根据 state_reached 返回 failure_recovery 格式的 recovery_hint。
    返回 None 表示不可恢复（终止重试）。
    """
```

---

## 6. 固件日志规范建议（Firmware Log Spec）

### 6.1 必须输出的日志（ESP32 Instrument 固件）

```c
// 固件启动序列（顺序输出）
ESP_LOGI(TAG, "AEL instrument firmware starting...");
vTaskDelay(pdMS_TO_TICKS(100));  // 确保 PC 端来得及接收

ESP_LOGI(TAG, "wifi connecting...");
// ... wifi init ...
ESP_LOGI(TAG, "wifi connected ssid=%s", ssid);
vTaskDelay(pdMS_TO_TICKS(50));

ESP_LOGI(TAG, "ip=" IPSTR, IP2STR(&event->ip_info.ip));
vTaskDelay(pdMS_TO_TICKS(50));

ESP_LOGI(TAG, "server ready port=443");
vTaskDelay(pdMS_TO_TICKS(50));

ESP_LOGI(TAG, "AEL S3JTAGboard is OK");  // ← 这行是 AEL 的 "ready" 信号
vTaskDelay(pdMS_TO_TICKS(100));
```

### 6.2 Heartbeat（必须实现）

```c
// 主循环或独立任务中，每 3 秒输出一次
static void heartbeat_task(void *arg) {
    for (;;) {
        ESP_LOGI(TAG, "heartbeat");
        vTaskDelay(pdMS_TO_TICKS(3000));
    }
}
```

**原因**：heartbeat 让 AEL 在长时间测试中随时可确认 instrument 仍然活着。

### 6.3 日志格式规范

| 要求 | 规范 | 反例 |
|------|------|------|
| 使用固定关键字 | `"wifi connected"` | `"WiFi up and running! 🎉"` |
| ip 使用 `ip=x.x.x.x` 格式 | `ip=192.168.2.251` | `my ip is 192.168.2.251` |
| ready 信号统一 | `"AEL S3JTAGboard is OK"` 或 `"instrument ready"` | `"everything seems fine"` |
| 关键行后加 delay | `vTaskDelay(100ms)` | 连续高速输出无间隔 |
| 不用 printf | 使用 `ESP_LOGI(TAG, ...)` | `printf(...)` (无 tag，难以过滤) |

### 6.4 `firmware_log_spec.py` — AEL 侧常量定义

```python
# 与固件日志规范对齐的正则常量
PATTERN_BOARD_READY = r"AEL.*board.*OK|board.*ready|instrument.*ready"
PATTERN_WIFI_CONNECTED = r"wifi.*connected|sta.*connected"
PATTERN_IP_ASSIGNED = r"ip=\d+\.\d+\.\d+\.\d+"
PATTERN_SERVER_READY = r"server.*ready|gdb.*ready|jtag.*ready|ws.*ready"
PATTERN_HEARTBEAT = r"heartbeat"

PATTERN_PANIC = r"Guru Meditation|panic|assert failed"
PATTERN_REBOOT = r"POWERON_RESET"  # 出现 ≥2 次
PATTERN_BOOTLOADER = r"boot:0x[0-9a-f]+ \(DOWNLOAD"
```

---

## 7. 与现有 AEL 流程集成

### 7.1 Test Plan Schema 扩展

在 instrument config YAML 中增加 `post_flash_verify` 节（可选，有默认值）：

```yaml
# configs/instrument_instances/s3jtag_rp2040_lab.yaml 示例
post_flash_verify:
  enabled: true
  port: /dev/ttyUSB0          # 串口设备路径
  baud: 115200
  expected_state: instrument_ready
  boot_timeout_s: 10
  capture_window_s: 15
  heartbeat_confirm_s: 5
  max_recovery_attempts: 2
```

### 7.2 Flash Action 集成点

在 `run_flash()` 返回 `status: success` 后，调用方（runner）检查 instrument config 是否有 `post_flash_verify.enabled=true`，若有则执行 `PostFlashVerifier.verify()`。

**不在 `run_flash()` 内部耦合**，而是在 runner 层作为独立步骤，理由：
- flash action 属于 instrument backend，不应直接依赖串口
- 便于单独测试和 mock
- 可在 test plan 中以独立 step 类型 `post_flash_verify` 出现

### 7.3 RunPaths 扩展

```python
# ael/run_manager.py 新增字段
post_flash_verify_log: Path   # 原始串口日志
post_flash_verify_json: Path  # 判定结果 JSON
```

### 7.4 Test Plan Step 类型

```json
{
  "type": "post_flash_verify",
  "inputs": {
    "port": "/dev/ttyUSB0",
    "baud": 115200,
    "expected_state": "instrument_ready",
    "boot_timeout_s": 10,
    "capture_window_s": 15
  }
}
```

---

## 8. 错误报告规范

### 8.1 成功时

```json
{
  "status": "success",
  "action": "post_flash_verify",
  "data": {
    "state_reached": "instrument_ready",
    "matched_patterns": ["board_ready", "wifi_connected", "ip_assigned", "service_ready"],
    "missing_patterns": [],
    "heartbeat_confirmed": true,
    "elapsed_s": 8.3
  }
}
```

### 8.2 失败时（明确区分 flash 成功 vs runtime 失败）

```json
{
  "status": "failure",
  "action": "post_flash_verify",
  "failure_kind": "runtime_bringup_failed",
  "summary": "flash succeeded but runtime bring-up failed",
  "data": {
    "flash_status": "success",
    "state_reached": "crash",
    "matched_forbidden": ["firmware_panic"],
    "missing_patterns": ["wifi_connected", "ip_assigned", "service_ready"],
    "recovery_attempts": 2,
    "raw_log_excerpt": "...",
    "elapsed_s": 35.1
  },
  "recovery_hint": {
    "kind": "runtime_bringup_failed",
    "recoverable": false,
    "preferred_action": "inspect_serial_log",
    "reason": "firmware_panic_detected_after_flash"
  }
}
```

**关键**：`failure_kind` 使用新常量 `"runtime_bringup_failed"`，与现有 `transport_error` / `timeout` 明确区分，不会被误识别为网络问题。

---

## 9. 实现顺序（推荐）

1. **`firmware_log_spec.py`** — 先定义常量和 pattern，是后续所有组件的基础
2. **`state_matcher.py`** — 纯逻辑，可先写单元测试
3. **`verifier.py`** — 编排器，依赖 state_matcher + 现有 transport
4. **`recovery.py`** — 恢复策略，集成 failure_recovery
5. **修改 `run_manager.py`** — 增加 RunPaths 字段
6. **修改 instrument config YAML** — 为 s3jtag_rp2040_lab 增加 `post_flash_verify` 节
7. **更新 ESP32 instrument 固件** — 增加规范日志 + heartbeat
8. **端到端验证** — 用 s3jtag_rp2040_lab 跑一次完整 flash + verify 流程

---

## 10. 关键决策记录

| 决策 | 理由 |
|------|------|
| verify 在 runner 层，不耦合进 flash action | 保持 backend 纯粹，便于测试 |
| 用 RTS/DTR 复位而非 power cycle | AEL 已有 `control_reset_serial`，无需硬件改动 |
| heartbeat 间隔推荐 3s | 1s 对 ESP-IDF logging 来说输出量合适；3s 更省资源，AEL 等待窗口内能看到至少 1 次 |
| 关键日志后加 `vTaskDelay(50-100ms)` | 防止 UART TX FIFO 溢出 + PC 端串口缓冲未 flush |
| profile 系统（instrument_ready / boot_only / custom）| 避免硬编码，支持不同固件类型 |
| `flash_succeeded_but_runtime_failed` 作为独立 failure_kind | 与 transport_error、timeout 明确隔离，防止错误归因 |

---

## Civilization Engine Usage Audit

查询了什么：本文档为设计阶段，尚未开始实现，未查询 CE
命中了什么：无
是否复用：N/A
新增记录：无（待实现完成后记录）
升级资产：无
