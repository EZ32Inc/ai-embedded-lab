# Experience Engine v0.1 Spec — Conceptual

**Status:** Draft
**Date:** 2026-03-22
**Source:** Extracted from AEL design discussion with ChatGPT

---

## 1. 定义（Definition）

> Experience Engine v0.1 = 一个持续接收经验，将其结构化、存储、可调用，并通过反馈不断进化的核心系统。

**核心不是：**
- UI
- agent
- chatbot

**核心是：**
> 经验的生命周期管理系统

---

## 2. 架构定位（非常重要）

Experience Engine 不是 AEL 的子层，也不是 KnowThyself 的子组件。

它是**独立基础组件**，AEL 和 KnowThyself 都依赖它：

```
AEL ──┐
      ├──→ depend on Experience Engine
KnowThyself ──┘

(其他项目也可以依赖它)
```

类比关系：Experience Engine 对 AEL/KnowThyself，类似 PostgreSQL 对 Django/Rails — 通用基础设施，供多个项目使用。

**部署方式：** 其他项目通过 git submodule 或类似方式引入。

---

## 3. 核心能力（Core Capabilities）

### 3.1 Continuous Intake（持续输入）
系统必须支持不断接收新的 experience，来源包括：
- AEL（engineering domain）
- KnowThyself（self domain）

### 3.2 Processing Pipeline（处理管线）
每条输入必须经过：
```
normalize → chunk（必要时）→ summarize → tag → classify → structure
```

### 3.3 Structured Experience Storage（结构化存储）
系统不存"原始数据"，而是存 **Experience Units**。

### 3.4 Retrieval（可调用）
系统必须支持：
- **Evidence Retrieval**：找相关经历
- **Principle Retrieval**：找经验/规律

### 3.5 Feedback Loop（反馈闭环）
系统必须支持 `correct / wrong / adjust`，用于更新经验、提高置信度、优化选择。

### 3.6 Evolution（进化）
系统必须支持经验升级、schema 升级、策略优化，包括：
- `schema_version`
- `success_count / confidence`
- 新旧共存

---

## 4. 核心数据结构（Experience Unit）

```json
{
  "id": "...",
  "schema_version": "v1",

  "domain": "engineering | self",
  "type": "...",

  "intent": "...",

  "raw": "...",
  "summary": "...",

  "context": {},
  "tags": [],
  "entities": [],

  "actions": [],
  "outcome": "success | partial | failed",
  "confidence": 0.8,

  "related_experience": [],
  "derived_from": [],

  "timestamp": "...",
  "source": "...",

  "feedback": null
}
```

---

## 5. 四层结构（非常关键）

```
Layer 1 — Raw         原始数据（不丢）
Layer 2 — Summary     可检索
Layer 3 — Distilled   经验 / 模式
Layer 4 — Operational 可执行规则
```

---

## 6. 双域支持（AEL + KnowThyself）

**Engineering Domain（AEL）**
- debug, migration, build, fix

**Self Domain（KnowThyself）**
- thinking, interest, decision, reflection

统一方式：
- `domain` 字段区分
- engine 完全共享

---

## 7. Experience Lifecycle（核心循环）

```
Intake
  → Process
  → Store
  → Retrieve
  → Apply
  → Feedback
  → Evolve
```

这是系统最重要的循环。

---

## 8. 系统目标（v0.1）

**不是：**
- 完整智能系统
- 自动 agent

**而是：**
1. 能记录经验
2. 能被再次使用
3. 第二次更好

---

## 9. 成功标准（v0.1）

> v0.1 成功 = 做一次 → 记录 → 再做一次 → 更快 / 更准

---

## 10. 系统哲学

> We do not store data. We accumulate experience.

> We do not retrieve information. We reuse learning.

> The system does not just remember — it improves.

---

## 11. 三个方向级补充

### 11.1 Experience Engine ≠ 数据系统，而是"决策基础设施"

Experience Engine 的终极作用，是支撑**决策**。否则容易走向：日志系统 ❌、知识库 ❌、vector DB ❌。

正确方向是：决策支持系统 ✔

区别：
- ❌ 数据系统：查到 `ADC driver removed`
- ✅ Experience Engine：决策 → 用新 API → 不要尝试 legacy workaround → 优先路径是 X

所有设计都可以问一句：**这能不能帮助"下一次决策更好"？**

### 11.2 Engine 的核心不是"记住"，而是"减少搜索空间"

AI 的一个核心问题是：可能性太多。

Experience Engine 的作用是**剪枝（pruning）**：
- 没有经验：100种可能
- 有经验：只剩 3 种路径

**不是增加信息，而是减少不必要的尝试。**

### 11.3 Executable Second Brain

很多人会把这个类比成 Notion、Obsidian、PKM，但本质是：

- ❌ 人在用系统
- ✅ 系统在替人思考 + 行动

更准确是：**Executable Second Brain**

---

## 12. 五个关键设计埋点

### 12.1 Experience 要有"scope"
```json
"scope": "task | project | long_term"
```
避免 task 级经验被错误提升为 long_term 规则。

### 12.2 引入"decay / aging"（非常关键）
旧经验可能已经过时。加入：
```json
"last_used": timestamp
"decay_score": 0.2
```
用于：新经验 > 旧经验。

### 12.3 "negative experience"（非常重要）
```json
"outcome": "failed"
"avoid": true
```
失败经验比成功经验更有价值，用于主动避免错误路径。

### 12.4 "confidence ≠ correctness"
- `confidence` = 系统相信程度
- `correctness` = 真实是否正确

未来可演化为：
- `confidence`（系统）
- `validation`（现实验证）

### 12.5 Experience 的"组合能力"（未来会爆炸强）

多个 experience 组合：
```
IDF migration
+ UART conflict
+ SPI config 经验
→ 自动解决复杂问题
```

---

## 13. 三个"未来大招"

### 13.1 Auto Skill Generation
Experience 累积到一定程度，自动生成 skill：
```
if error contains X → apply fix Y
```
这就是 AEL Civilization 的自动化版本。

### 13.2 Personalization Layer（连接 KnowThyself）
同一个问题，不同用户 → 不同答案（context-aware decision）。

### 13.3 Self-Reflection（非常强）
系统可以问自己：**我最近做错最多的地方是什么？**
这就是 meta-learning。

---

## 14. 最终总结

你现在已经完成了三件非常关键的事：
1. 把问题从"项目"提升到"基础设施"
2. 把数据提升到"experience"
3. 把 memory 提升到"lifecycle"

> **Experience Engine is not proven by design — it is proven by repeated use.**

---

*Extracted from AEL design discussion. Date: 2026-03-22*
