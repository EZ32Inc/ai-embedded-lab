# Spec: 任务五件套闭环规则 v0.1

## Status
Draft — adopted from STM32G431 bring-up experience (2026-03-16)

---

## Purpose

建立一条默认工作规则：

对于任何新的 bring-up / validation / debug / integration 任务，完成标准不应只包括技术结果，还应包括过程记录、经验提炼和可复用资产沉淀。

目标是让 AEL 不只是"把事情做成"，而是每做成一件事，系统都能为下一次默认变得更强。

---

## 1. 为什么需要这条规则

一个任务即使技术上已经完成，也常常会遗漏掉更有长期价值的部分：

- 过程是怎么走到结果的
- 中间踩了哪些坑
- 哪些修复只是局部补丁，哪些其实是通用规律
- 哪些经验应该沉淀成 skill / workflow / spec
- 下次再遇到类似任务，默认应该先做什么

如果这些内容没有被主动提取出来，高价值经验会停留在临时对话和短期记忆里，难以复用。

因此，任务完成不能只看 test 是否 pass、board 是否 verified、feature 是否实现，还要看：

- 过程是否记录
- 经验是否提炼
- 规则是否形成
- 默认做法是否更新

**核心原则：任务完成，不只是"做通了"，还包括"为下一次默认更强做了什么准备"。**

---

## 2. 五件套定义

对于任何新的任务，默认应尽量产出以下五类内容。

### 2.1 本次任务总结

回答：这次做了什么 / 目标是什么 / 最终达到了什么状态。

典型内容：board / target / feature 名称，任务范围，最终结果，当前状态变化（例如 promoted to verified）。

---

### 2.2 关键失败与修复

回答：中间最关键的问题是什么 / 真正的根因是什么 / 是怎么修好的。

典型内容：symptom、root cause、exact fix、why the fix is correct、what evidence supported the diagnosis。

---

### 2.3 新学到的规则

回答：这次学到了什么新规则 / 哪些隐含假设被推翻了 / 哪些判断应成为今后类似任务的默认约束。

典型内容：新 family bring-up 的规则、风险识别规则、code review 关注点、默认流程顺序。

---

### 2.4 可复用的 skills / workflow 改进

回答：这次长出了什么新能力 / 哪些方法应沉淀成 skill、spec 或工作流增强 / 哪些机制以后可以直接复用。

典型内容：wiring auto-discovery、pair-level GPIO sanity validation、debug mailbox result reporting、新的调试/验证策略。

---

### 2.5 下次应成为默认的做法

回答：下次再遇到类似问题，什么应该直接作为默认动作 / 哪些步骤不应再从零想起 / 哪些顺序应固定下来。

典型内容：先做三线 debug mailbox 最小闭环、再做 pair-level GPIO sanity、再进入复杂外设模式验证、优先参考 target-family CubeMX/LL 初始化。

---

## 3. 两段式执行方式

这条规则应分为两个阶段执行，而不是只在任务结束后才想起来。

### 3.1 开始前：五件套前置声明

在任务开始时，明确：本次任务除了技术目标，还要尽量产出五件套。

建议做一个简短任务简报，包含：

- 本次技术目标是什么
- 本次预计会重点关注哪些风险
- 本次希望记录哪些过程
- 本次结束时应尽量交付哪五类内容

**示例（STM32G431 bring-up）：**
- 技术目标：完成 STM32G431 8-test bring-up
- 过程目标：记录失败点、调试路径、family-specific 差异
- 资产目标：形成 postmortem、rule、workflow update、skill 候选

这样做的意义：做的时候就会主动注意过程，不会等做完才发现很多信息没记录。

---

### 3.2 结束前：五件套完成检查

任务结束前，固定用五个问题做 closure：

1. 这次做成了什么？
2. 中间最关键的失败和修复是什么？
3. 这次新学到了什么规则？
4. 这次长出了什么可复用能力？
5. 下次默认该怎么做？

追加检查项：

- 是否只记录了结果，没记录过程？
- 是否只记录了 bugfix，没提炼规则？
- 是否有值得变成 spec / memo / skill 的内容未被提取？
- 是否有新的默认流程应该更新但还没写出来？

---

## 4. 进行中的记录要求

为了让结束时真正能产出五件套，任务进行中应主动记录以下关键节点：

- 关键现象
- 关键假设
- 关键实验
- 关键证据
- 关键修复
- 关键分层判断
- 值得沉淀的方法变化

重点不是记录所有细节，而是记录那些影响根因判断、工作流变化、规则形成、能力复用的关键节点。

---

## 5. 产出物形式与存放位置

五件套不要求都写成同一种文档，可以按实际情况分别变成：

| 内容类型 | 推荐形式 | 推荐位置 |
|---|---|---|
| 任务总结 | summary memo | `docs/postmortems/` |
| 关键失败与修复 | postmortem | `docs/postmortems/` |
| 新规则 | spec / rule doc | `docs/specs/` |
| 可复用 skill / workflow | skill doc | `docs/skills/` |
| 下次默认做法 | workflow note / memory update | `docs/specs/` 或 memory |
| 未来待做事项 | backlog entry | `docs/specs/future_improvements_v0_1.md` |

重点不是形式统一，而是内容不要漏。

---

## 6. 适用范围

这条规则适用于：

- new board bring-up
- smoke pack 建立
- debug 任务
- validation / verification 任务
- workflow / infrastructure 改进
- 新测试机制引入
- bench reality clarification
- instrument / network / interface integration

只要任务中有真实问题、真实实验、真实修复，就应该尽量适用这条规则。

---

## 7. 为什么这条规则很重要

### 7.1 它让系统从"会做事"变成"会积累能力"

没有这条规则，系统完成一个任务最大的收获可能只是一个结果、一个修复、一个通过状态。

有了这条规则，系统每完成一个任务，都更可能额外得到：一个总结、一个 postmortem、一条规则、一个 skill、一个新的默认流程。这就是能力增长。

### 7.2 它把经验资产化

很多最宝贵的经验不是最终结果，而是：

- 为什么一开始错了
- 为什么某种方法更好
- 哪一步应该前置
- 哪些假设不应默认成立

这些内容如果不主动资产化，很容易丢失。

### 7.3 它鼓励"过程也是产品"

对于 AEL 这种系统来说，真正长期有价值的不是某次单次成功，而是：

- 系统怎么越来越会成功
- 系统怎么越来越少踩同样的坑
- 系统怎么越来越会把现实问题变成通用能力

---

## 8. STM32G431 案例说明

STM32G431 bring-up 是这条规则的动机案例。

在这次过程中，最终不只是完成了 smoke_stm32g431 8/8 PASS 和 STM32G431CBU6 promoted to verified，还提炼出了多类高价值资产：

**关键失败与修复**
- SPI：FRXTH / FIFO threshold / SPE enable 顺序
- ADC：CKMODE / common clock source

**新规则**
- 新 family bring-up 不应默认复用旧 family 外设实现
- 要警惕 missing transplant
- 要警惕 implicit assumption from prior family knowledge

**新能力 / skill**
- wiring auto-discovery（Method A / Method B）
- frequency-coded parallel mapping inference
- pair-level GPIO sanity validation
- debug mailbox result path

**下次默认做法**
- 先三线 + mailbox 确认程序运行
- 再做 pair-level GPIO sanity
- 再进入复杂外设验证
- 优先参考 target-family CubeMX/LL init

这正说明：如果任务结束时能够主动检查"五件套"，就能把一次 bring-up 变成多层系统能力增长。

---

## 9. 风险与注意事项

### 9.1 不要追求形式主义

五件套的目标是沉淀价值，不是机械填表。如果一项确实没有新的内容，应明确说明，而不是硬凑。

### 9.2 不要求一开始就完美

开始时可以先求"有"，再逐步提高质量。

### 9.3 重点在关键节点

不需要记录所有过程，而要记录那些真正影响结论、规则和复用价值的关键点。

---

## 10. 成功标准

这条规则实施成功的标志：

- 任务开始前就有五件套意识
- 任务过程中主动记录关键现象与证据
- 任务结束时不只汇报结果，还能汇报经验资产
- 类似任务中开始出现"默认更强"的行为
- 系统越来越少重复犯同类错误
- bring-up / debug 的每次成功都能明显增强系统能力

---

## 一句话总结

**对于任何新的 bring-up / validation / debug / integration 任务，完成标准不应只包括技术成功，还应包括"五件套"经验资产闭环：任务总结、关键失败与修复、新规则、可复用 skills/workflow 改进，以及下次应成为默认的做法。**
