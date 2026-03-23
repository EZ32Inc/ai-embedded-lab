# AEL Civilization Engine — ESP32-C6 / C5 Bring-up 经验沉淀（V1）

**Date:** 2026-03-23
**Status:** Validated — Production Ready

---

## 🎯 目标

将 ESP32-C6 → ESP32-C5 的调试过程，从一次性工程经验，转化为：

> AEL Civilization Engine 可复用的标准方法（reusable method）

核心要求：

| 属性 | 含义 |
|------|------|
| 可迁移 | C6 → C5 → 未来所有 MCU |
| 可复用 | 无需重新探索 |
| 可降级 | 无仪器也能运行 |
| 可生产 | 分钟级完成 |

---

## 📊 一、关键现象（必须记录）

| 阶段 | 时间 | 特征 |
|------|------|------|
| C6 初次 bring-up | ~5 小时 | 人工试错、接线错误、流程不稳定 |
| C5 bring-up | ~5 分钟 | 一次成功、无试错、流程稳定 |

**结论：系统从"探索模式"跃迁到"确定性生产模式"**

---

## 🧱 二、核心方法（必须进入 Civilization Engine）

**方法名称：Minimal-Instrument Board Bring-up Pattern**

### Step 1 — 板级抽象（Board Definition）

```
定义：
  - flash path    （USB / UART — 用 serial number 固定，不依赖 /dev/ttyACMx 编号）
  - console path  （UART / USB CDC — 与 flash path 分离）
  - 可用 GPIO     （safe IO，不与 strap / USB / boot pin 冲突）
  - 禁用资源      （strap / USB D+D- / boot sequence pin）
  - 外部仪器      （LA / JTAG — 可选，可降级）
```

**作用：** 从源头消除"接线错误 / 资源冲突"类人为故障。

C6 实例：
- Flash serial: `40:4C:CA:55:5A:D4`（Native USB）
- Console serial: `58CF083460`（CH341 UART0 bridge）
- Safe GPIO: 15, 18–23

C5 实例：
- Flash serial: `3C:DC:75:84:A6:54`（Native USB Serial/JTAG）
- Console serial: `5AAF278818`（CH341 UART0 bridge，GPIO11 TX / GPIO12 RX）
- Safe GPIO: 0–7, 9, 15

---

### Step 2 — 最小硬件配置（Minimal Wiring）

```
必须：
  - USB ×2（flash port + console port）
  - 1 根 loopback jumper（如 GPIO2 ↔ GPIO3）

禁止：
  - 初期依赖外部仪器（LA / JTAG / 示波器）
```

**原则：先建立"最小闭环系统"，再逐步加复杂度。**

> 如果有仪器（LA），可附加接线用于信号观测。但 PASS/FAIL 判定
> 不能依赖仪器可用性——仪器应作为"增强验证层"，而不是"必要条件"。

---

### Step 3 — 标准测试序列（Canonical Test Suite）

固定顺序（**顺序非常关键**，从软到硬，从内到外）：

| 序号 | 测试 | 类型 | 说明 |
|------|------|------|------|
| 1 | AEL_TEMP | 内部资源 | 验证 runtime / driver 可用 |
| 2 | AEL_NVS | 存储系统 | Flash 读写闭环 |
| 3 | AEL_SLEEP | 电源 / timer | 低功耗唤醒机制 |
| 4 | AEL_BLE | RF（低复杂度） | BLE scan，3 s passive |
| 5 | AEL_WIFI | RF（高复杂度） | Wi-Fi scan，含 5G（C5 专属） |
| 6 | AEL_PWM | 外设输出 | LEDC，可降级为软件验证 |
| 7 | AEL_PCNT | 物理闭环 | 脉冲生成 + 硬件计数，关键 |

**原则：从"纯软件 → 系统服务 → RF → 硬件闭环"逐步推进。**

---

### Step 4 — 自闭环物理验证（On-board Loopback）

核心模式：

```
GPIO_A （output）→ 物理跳线 → GPIO_B （input/counter）
发送已知信号 → 硬件采样/计数 → 软件校验
```

本次实例（C5 / C6 通用）：

```
GPIO_DRIVE → GPIO_INPUT
100 pulses  →  PCNT  →  counted = 100  →  PASS
```

**这是 Civilization Engine 必须记录的关键能力：无需外部仪器的真实电气验证方法。**

PCNT 闭环验证的意义：
- 证明 GPIO 输出电平正常（数字信号完整）
- 证明 GPIO 输入采样正常（内部外设工作）
- 证明 MCU 实时控制时序正常（busy-delay 精度）

---

### Step 5 — 仪器降级策略（Instrument Degradation）

当没有 LA / 示波器时：

| 测试 | 有仪器 | 无仪器（降级策略） |
|------|--------|-------------------|
| PWM 频率/占空比 | LA 测量，接受范围校验 | 软件验证（driver config PASS = PASS） |
| GPIO toggle 观测 | LA edge count | 跳过（不影响 PCNT 闭环） |
| 时序精度 | 逻辑分析仪 | 不验证 |
| RF 功率 | 频谱仪 | 不验证 |

**原则：先保证功能正确，再提升验证精度。降级不是妥协，是分层策略。**

---

### Step 6 — 环境敏感项处理（RF 特别重要）

Wi-Fi / BLE 测试的 PASS 条件：

```
PASS 条件（环境无关）：
  - 驱动初始化成功（err = 0）
  - scan 流程成功完成（无 crash / timeout）
  - 返回数据结构合法

PASS 条件（环境相关，不作为强判定）：
  - AP 数量 > N      → 仅作参考（实验室可能无信号）
  - BLE 广播数 > N   → 仅作参考（空旷环境可能为 0）
```

**Civilization Engine 必须区分：功能失败 vs 环境无信号。**

C5 的额外 RF 特性：
- 全球唯一支持 5 GHz Wi-Fi 的低功耗 ESP32（WIFI_BAND_MODE_5G_ONLY）
- 测试时分别扫描 2.4G 和 5G，任一有信号即 PASS

---

## 🔁 三、跨板迁移模式（C6 → C5 的本质）

```
Board_A（C6）→ 提取 Pattern → Board_B（C5）
```

迁移内容（**复用，不重新探索**）：

- 测试结构（7 项顺序）
- 执行流程（build → flash → reset → UART read → parse → verdict）
- Loopback 思路（GPIO_DRIVE → GPIO_INPUT via jumper）
- USB 角色拆分（native USB = flash，CH341 = console）
- RF PASS 判定逻辑（驱动成功 + scan 完成）
- 分区策略（BLE+WiFi binary > 1 MB → 1920 K custom partition）

仅替换内容（**板级差异**）：

- Serial number（flash port / console port）
- GPIO 编号（safe IO list）
- Wi-Fi band API（C5 用 `esp_wifi_set_band_mode()`，C6 单频）
- IDF_TARGET（`esp32c5` / `esp32c6`）

**关键能力（必须写进 Engine）：**

> 当新板与已知板"同一家族 / 相似架构"时：
> → 不重新探索
> → 直接复用 test pattern
> → 只替换 board definition
>
> 探索成本 → 0

---

## ⚙️ 四、AEL Civilization Engine 应记录的 Skill

```yaml
skill:
  name: minimal_instrument_board_bringup

trigger:
  - bring-up new MCU board (same family or similar architecture)
  - "new board, same pattern as X"

fix:
  apply Minimal-Instrument Bring-up Pattern:
    1. define board (flash serial, console serial, safe GPIO)
    2. minimal wiring (USB ×2 + 1 loopback jumper)
    3. canonical test suite (TEMP → NVS → SLEEP → BLE → WIFI → PWM → PCNT)
    4. on-board loopback validation (PCNT pulse count)
    5. instrument degradation if no LA/JTAG

lesson:
  once a board pattern is established, new boards can be validated
  deterministically without trial-and-error

scope:
  esp32 family / RISC-V MCU boards / similar embedded platforms

evidence:
  C6 → C5: 5 hours → 5 minutes, 0 errors, first-run PASS
```

---

## 📈 五、能力等级跃迁（必须记录）

本次达成：

```
Level 4 — Instrument-Free Full Validation

特征：
  ✅ 无外部仪器（无 LA / JTAG）
  ✅ 全系统测试（含 RF：Wi-Fi 双频 + BLE）
  ✅ 含物理闭环验证（PCNT pulse loopback）
  ✅ 一次 PASS（0 次试错）
  ✅ 跨板复用（C6 pattern → C5 直接迁移）
```

**这是 Civilization Engine 的一个能力里程碑。**

---

## 🚀 六、可复用产物（已落地）

| 产物 | 路径 | 状态 |
|------|------|------|
| C6 固件套件 | `firmware/targets/esp32c6_suite_ext/` | ✅ committed |
| C6 实验脚本 | `experiments/esp32c6_suite_ext.py` | ✅ committed |
| C5 固件套件 | `firmware/targets/esp32c5_suite_ext/` | ✅ committed |
| C5 实验脚本 | `experiments/esp32c5_suite_ext.py` | ✅ committed |
| C6 GPIO/UART/ADC 基础套件 | `firmware/targets/esp32c6_gpio_loopback/`<br>`firmware/targets/esp32c6_hw_suite/` | ✅ committed |

建议后续补充：

```
experiments/templates/esp32_minimal_bringup_template.py   — 参数化模板
ael/patterns/loopback/pcnt_loopback.py                    — PCNT 模式复用模块
docs/boards/esp32c6_bringup_notes.md                      — C6 板级经验
docs/boards/esp32c5_bringup_notes.md                      — C5 板级经验
```

---

## 🧠 七、最核心结论

```
工程从 Exploration（探索）→ Production（生产）

根本原因：
  - 方法被结构化（Pattern 化）
  - 经验被系统记住（Civilization Engine）
  - 流程可复用（新板不再是"项目"，而是"执行"）

量化体现：
  时间：   5 小时 → 5 分钟  （60× 提速）
  错误：   多次试错 → 0 次  （消除探索成本）
  行为：   探索性 → 确定性  （质的跃迁）
```

---

## 🧩 八、对 Civilization Engine 的意义

这次 C6 → C5 不是一次 bring-up，而是证明：

> **Civilization Engine 已具备"经验积累 → 跨任务复用 → 指数级提速"的能力。**

具体体现：

| 维度 | C6（第一次） | C5（复用） |
|------|-------------|-----------|
| 接线 | 探索 + 出错 | 直接正确 |
| 分区 | 运行时发现问题 | 提前正确配置 |
| Reset 时序 | 多次调试 | 第一次正确 |
| RF 判定 | 反复校准阈值 | 直接复用逻辑 |
| 总耗时 | ~5 小时 | ~5 分钟 |

---

## ✅ 结语

> **Once a board bring-up pattern is learned, it becomes a reusable civilization asset.**
> **New boards are no longer "projects", but "executions".**
