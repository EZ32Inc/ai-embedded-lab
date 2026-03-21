# AEL Architecture Gaps & Next Steps

**Date:** 2026-03-20
**Status:** Draft (Strategic)

## 0. 背景

当前 AEL 已达到：

- Schema 收敛
- 多平台稳定运行
- 并行验证通过

系统进入：**Stable Execution System**

## 1. 已具备层

| 层 | 状态 |
|---|---|
| DUT | ✔ 部分存在 |
| Instrument | ✔ 部分标准化 |
| Test | ✔ |
| Process（pre-flight / execution） | ✔ |
| Schema | ✔ 已强化 |

## 2. 新识别的关键缺口

### 🔥 2.1 Connection / Setup Layer（关键缺口）

**问题：**

- 接线 / 上电 / boot 未结构化
- AI 无法判断 setup 是否正确

**解决：**

→ 引入 Connection Layer（见 Memo 1）

---

### 🔥 2.2 DUT 标准化（重要缺口）

**问题：**

- DUT 信息分散在 config / test / code
- AI 无法系统性理解 DUT

**目标结构：**

```
dut =
  identity
  interfaces
  capabilities
  requirements
  mappings
```

---

### 🔥 2.3 Instrument Backend + Interface 统一（正在做）

**问题：**

- ESP32 meter / JTAG / ST-Link 不对称

**目标结构：**

```
instrument =
  backend/
  transport/
  capability/
  actions/
```

---

### 🔥 2.4 Mapping / Compatibility（隐式缺口）

**问题：**

- 哪些组合可用，目前是隐式

**需要显式：**

```
mapping =
  dut ↔ instrument
  dut ↔ test
  test ↔ instrument
```

---

### 🔥 2.5 Process → 状态机化（增强项）

**当前：** 流程存在，但不可推理、不可验证

**目标：**

```
process =
  states
  transitions
  validation points
```

## 3. 架构整体图（目标）

```
AEL System

  DUT Layer
  Instrument Layer
  Connection Layer   ← 新增
  Test Layer
  Mapping Layer      ← 显式化
  Process Layer
  Schema Layer
  Insight Layer      （下一步）
  Regression Layer   （下一步）
```

## 4. 推荐实施顺序

| 优先级 | 步骤 | 内容 |
|---|---|---|
| 🥇 Step 1（立即） | Instrument 统一 | ✔ backend/interface 统一 |
| 🥈 Step 2（紧接） | Connection Layer | ✔ 最小实现 → **最大稳定性收益** |
| 🥉 Step 3 | DUT 标准化 | ✔ 最小 contract |
| Step 4 | Mapping Layer | ✔ 显式化兼容性 |
| Step 5 | Insight / Regression | ✔ Exploration |

## 5. 核心原则（必须坚持）

### 1. 不做"大设计"，先做最小可用

每一层：

- small schema
- real usage
- quick iteration

### 2. AI-first（非常关键）

所有层必须：

- AI 能读
- AI 能推理
- AI 能使用

### 3. 显式化优先

把以下内容转成结构化 contract：

- 隐式假设
- 人类经验
- scattered config

### 4. 不破坏现有稳定性

所有改动必须通过：

- default verification
- 多轮运行

## 6. 成功标志

系统达到：

- AI 不再"猜"
- setup / DUT / instrument 都可推理
- 新 board 接入可模板化
- 错误在 pre-flight 阶段被发现

## 7. 一句话总结

> 下一阶段的本质不是扩展功能，而是让系统结构闭合。
