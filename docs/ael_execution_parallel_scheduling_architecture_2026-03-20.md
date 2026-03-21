# AEL Execution & Parallel Scheduling Architecture

**Date:** 2026-03-20
**Status:** Draft (Architecture Review)

## 0. 背景

当前系统已经验证：

- 多平台（ESP32 / RP2040 / STM32）
- 多 instrument（ST-Link / ESP32 JTAG / meter）
- 6-way 并行执行
- 多轮运行无 flakiness

这说明：**AEL 已具备基础并行执行能力**

但尚未回答更关键的问题：

> ❗ 并行执行的架构模型是否清晰、是否可扩展、是否资源可控

## 1. 本 Memo 目标

定义并明确：

```
execution layer =
  concurrency model
  resource model
  scheduler
  isolation model
  scaling strategy
```

并作为未来以下能力的基础：

- 大规模实验（40 / 400 并行）
- AI-driven exploration
- regression system

## 2. 当前状态（Observed Behavior）

### 2.1 已验证能力

- 多 run 可并行执行
- 各 run 独立完成
- 无明显资源冲突
- 无交叉污染（当前规模）

### 2.2 隐含实现（推测）

当前系统很可能：

- 以 run 为单位并行
- 使用 subprocess / async task
- 简单调度（无复杂 scheduler）
- 资源控制：依赖"自然隔离"而非显式模型

### 2.3 当前问题

虽然运行正常，但存在未定义点：

- 并行单位未明确
- 资源边界未建模
- 调度策略未定义
- 隔离机制未 formalize
- 扩展路径未知

## 3. 核心设计问题

### 3.1 并行单位（Concurrency Unit）

必须明确：**What runs in parallel?**

候选单位：

| 候选 | 说明 |
|---|---|
| run | 当前最可能 |
| experiment | 多 run 组合 |
| instrument session | 单一仪器会话 |
| workflow step | 步骤级并行 |

**建议（v0.1）：以 run 为最小并行单位**

优点：简单、隔离清晰、与当前实现一致

### 3.2 资源模型（Resource Model）

必须显式建模：

```
resource =
  instrument
  port
  connection
  host cpu
  io channel
```

示例：

| 资源 | 占用模式 |
|---|---|
| ST-Link | exclusive |
| ESP32 JTAG | exclusive |
| serial port | exclusive |
| GPIO capture line | exclusive |

**关键原则：所有有限资源必须可声明、可占用、可释放**

### 3.3 调度模型（Scheduler）

当前：隐式调度

未来需要：

```
scheduler =
  queue
  resource allocation
  conflict resolution
```

最小设计（v0.1）：

- FIFO 队列
- resource locking
- run-level scheduling

后续可扩展：

- priority
- capability-aware scheduling
- load balancing

### 3.4 隔离模型（Isolation）

目标：**一个 run 不影响另一个 run**

必须保证：

- log 隔离
- temp 文件隔离
- instrument state 隔离
- connection 独占
- port 独占

> **原则：Isolation 必须是"设计保证"，不是"当前碰巧没问题"**

### 3.5 扩展模型（Scaling Strategy）

**维度 1：单机扩展**

6 → 12 → 24 runs，需要：更好的调度、资源跟踪、IO 管理

**维度 2：多机扩展（未来）**

multiple hosts，需要：distributed scheduler、remote instrument abstraction

**维度 3：AI exploration**

hundreds of experiments，需要：batch scheduling、result aggregation、adaptive execution

## 4. 新架构层定义

### 🔧 Execution / Scheduling Layer

```
execution layer =
  concurrency model
  resource model
  scheduler
  isolation
  scaling
```

### 与 Process Layer 的区别

| Layer | Role |
|---|---|
| Process | 做什么步骤 |
| Execution | 如何并发执行这些步骤 |

## 5. 与其他层的关系

### 5.1 与 Instrument Layer

- instrument = 资源
- scheduler 必须知道：是否独占、是否可复用

> **backend 统一是前提**

### 5.2 与 Connection Layer

- connection = 物理资源
- 不能同时被多个 run 使用

> **必须纳入 resource model**

### 5.3 与 DUT Layer

- DUT = execution target
- 某些 DUT 可能限制执行方式

### 5.4 与 Test Layer

- test 决定资源需求
- scheduler 需要知道：

```
test.requires:
  - instrument
  - connection
```

### 5.5 与 Mapping Layer

- mapping 决定合法组合
- scheduler 不能调度非法组合

### 5.6 与 Insight / Regression

- execution metadata → insight
- timing / resource → regression 分析

## 6. 推荐实施路径

| 阶段 | 内容 | 说明 |
|---|---|---|
| Phase 1（立即） | Execution Review（不改代码） | 明确并行单位；列出所有资源；标出隐式串行点；记录 6-run 成功原因 |
| Phase 2（最小模型） | 定义 resource model | 每个 run 声明使用哪些 resource；加 basic locking |
| Phase 3（轻量 scheduler） | run queue + resource-aware dispatch | 冲突避免 |
| Phase 4（扩展） | 优先级 / 多 host / AI exploration | — |

## 7. 成功标准

系统具备：

- 并行执行行为可解释
- 无隐式资源冲突
- run 隔离可靠
- 扩展到更高并行度无需重构
- AI 可以推理执行能力

## 8. 一句话总结

> **Execution Layer = 让"并行执行"从现象变成架构能力**

## 9. 最关键判断

当前阶段：

- ✔ 已验证并行可行
- ❗ 但未定义并行架构

下一步必须完成：

> 从"能并行跑" → "有清晰并行模型"

---

## 附录：Phase A 路线图理据

*以下是关于四步主线顺序的架构推理。*

### Phase A 主线

```
Instrument 统一 → Connection 补齐 → DUT 抽象 → Execution 建模
```

### Step 1：Instrument 统一

当前最直接、最成熟的一步。

- 不对称点已明确
- 问题边界清楚
- 工作量相对可控
- 做完以后，上层 schema 才真正有稳定依托

> 先把"工具侧"规范起来。

### Step 2：Connection 补齐

非常关键，直接提升系统稳定性。

很多真实问题不是代码、不是 DUT、不是 instrument，而是：
接线、电源、boot 条件、reset、physical setup。

Connection 是把"物理现实"正式纳入系统模型。
做完之后，AI 会少很多想当然。

### Step 3：DUT 抽象

放在 Connection 后面很合适，因为 DUT 的有效描述要结合：

- 它暴露什么接口
- 它需要什么 setup
- 它和哪些 instrument / test 能匹配

先把 Connection 层补出来，再抽象 DUT，DUT contract 会更完整、更不容易空泛。

### Step 4：Execution 建模

Execution/scheduling 的前提是先知道：

- 有哪些 instrument 资源
- connection 是什么资源
- DUT 有什么约束
- 哪些组合是合法的

否则 execution 会变成空中楼阁，只能讨论抽象并行，而没法落到真实系统上。

Execution 更像是前面三层逐渐清楚之后，自然收口出来的"运行内核"。

### 四步逻辑

| 步骤 | 对象 | 动作 |
|---|---|---|
| Step 1 | Instrument | 先统一**能做事的工具** |
| Step 2 | Connection | 再明确**世界是怎么连起来的** |
| Step 3 | DUT | 再定义**被操作的目标对象** |
| Step 4 | Execution | 最后建模**这些对象怎么被组织和并行执行** |

### Phase A 完成后

当这四步完成之后，以下工作会容易很多：

- Mapping / compatibility 显式化
- Insight layer
- Regression layer
- Scalable exploration

因为那时候核心结构已经比较完整了。

**Phase A 走完，系统会从"已经很强的 AI-driven execution system"进一步变成：结构闭合、可推理、可扩展的工程平台。**
