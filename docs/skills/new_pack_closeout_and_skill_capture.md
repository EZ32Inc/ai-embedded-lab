# New Pack Closeout And Skill Capture

## Purpose

定义一个强制性的收尾技能：每次新增或正式化一个 pack，并完成至少一次有意义的 live validation 后，必须把结果收口为 closeout 和 skill，而不能停在“代码已提交”。

## Why This Skill Exists

这份 skill 直接来自这次 `STM32F103 GPIO cross-instrument` 工作中的遗漏。

遗漏点不是实现失败，而是流程停止得太早：
- pack 已建好
- live validation 已完成
- commit 已完成
- 但 reusable knowledge 没有立即沉淀成 skill

这个遗漏的根因是把“代码提交完成”误当成了“任务闭环完成”。

在 AEL 里，这不够。
对于新 pack、新 bench pattern、真实排障修复，交付物应至少包括：
- code/config/test changes
- validation evidence
- closeout
- reusable skill extraction

## Why It Was Missed In This Case

这次漏掉，不是因为没有信息，而是因为流程判断错了。

错误判断链条是：
- 新 pack 已经创建
- live runs 已经完成
- 关键 bug 也已经修掉
- commit 也已经做了
- 然后把“实现已完成”误当成“知识也已经交付”

真正缺的不是更多测试，而是把这次得到的 reusable method 固化下来。

所以这个 skill 的第一目标不是补写文档，而是防止以后再次把：
- code completion
- validation completion
- knowledge completion

混成一件事。

## Trigger / When To Use

在以下任一情况后必须触发：
- 新增一个 pack 并完成 live run
- 新增一个 cross-instrument child/base pack family
- 修复一个真实 bench / verify / instrument 语义问题
- 将一个原本失败的路径修到稳定通过

## Scope

适用于：
- pack creation
- pack migration
- shared base + child pack patterns
- live validation closeout
- post-debug knowledge capture

不适用于：
- 纯局部代码整理
- 没有真实验证证据的草稿设计

## Required Inputs

- 新 pack 或 child/base pack 文件
- 相关 board / instrument / test / firmware 改动
- 至少一轮真实 run 或 pack run 的结果
- run ids
- 当前已知结论
- 当前仍未解决的问题

## Procedure

1. 确认 pack 已有明确边界。
   - shared 在哪里
   - instrument-specific 在哪里
2. 确认至少有一轮真实验证证据。
   - 单 test 或 full pack 都可以
   - 但必须有真实 run id
3. 写 closeout。
   - 记录 scope
   - 记录 pass/fail 结论
   - 记录 run ids
   - 记录当前结论和剩余问题
4. 提炼 reusable knowledge。
   - 哪些判断是可复用的
   - 哪些 debug 顺序是可复用的
   - 哪些误判以后应避免
5. 写成 `docs/skills/` 下的 skill 文档。
   - 至少一份流程 skill 或技术 skill
   - 需要时拆成两份
6. 明确写出“为什么这一步之前会漏掉”。
   - 这是流程改进的一部分
   - 不写清楚，遗漏会重复发生
7. 再决定是否提交。
   - commit 不是 closeout/skill capture 的替代品

## Required Outputs

至少应产出：
- 一个 closeout 文档
- 一个或多个 skill 文档
- run ids / evidence references
- 简短结论：模式是否成立、问题是否已收口
- 一段明确的遗漏原因与防再发说明

## Decision Rules

- 如果只是“跑通一次”，但模式以后会复用，应写 skill。
- 如果修的是工具链 / verify / instrument 语义问题，更应写 skill。
- 如果用户明显把这次工作当成 pattern 建设，而不只是单次修 bug，不能省略 skill capture。
- 如果已经开始写 closeout，就必须同时回答：
  - 为什么之前会漏掉这一步？
  - 以后靠什么规则避免再次漏掉？

## Common Pitfalls

- 把 commit 当作工作完成
- 只写 session summary，不写 reusable skill
- 只记录 pass，不记录为什么之前 fail
- 没把“结构性经验”和“单次现象”分开

## Recovery

如果已经做完实现但漏了这一步，应补做：
1. 回看 run ids 和 closeout 证据
2. 先总结遗漏原因
3. 再写流程 skill 和技术 skill
4. 最后补提交通常也可以接受

## Enforcement Rule

为防止再次遗漏，新的 pack 工作在以下条件同时满足前，不应视为完成：
- 新 pack / child pack 已落地
- 至少一轮 live validation 已完成
- closeout 已写
- `docs/skills/` 已新增或更新对应 skill
- 已明确写出“为什么这一步容易漏掉以及以后如何避免”

如果只完成了前两项或前三项，这仍然属于“未闭环”状态。

## Relationship To Other Skills

- 与 [validation_summary_emission_skill.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/validation_summary_emission_skill.md) 的关系：
  它负责成功结果摘要；本 skill 负责“成功之后必须把知识收口”
- 与 [last_known_good_extraction_skill.md](/nvme1t/work/codex/ai-embedded-lab/docs/skills/last_known_good_extraction_skill.md) 的关系：
  它负责提取 working setup；本 skill 负责把整个 pack-level 经验沉淀为可复用方法

## Current Known Conclusion

在 AEL 当前阶段，只要出现：
- 新 pack
- live validation
- 真实修复

就应把 `closeout + skill capture` 视为默认流程，而不是可选附加项。
