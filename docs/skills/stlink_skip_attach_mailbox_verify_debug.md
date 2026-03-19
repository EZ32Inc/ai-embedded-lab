# ST-Link Skip-Attach Mailbox Verify Debug

## Purpose

沉淀一个可复用的排障技能：当 `ST-Link + mailbox_verify` 在 `skip_attach` 路径下表现异常时，如何区分是 DUT/loopback 问题、firmware mailbox 问题，还是 `st-util` / GDB 语义问题。

## Scope

适用于以下现象：
- build 和 flash 成功
- test 在 `verify` 阶段失败
- mailbox 读取结果异常，尤其是：
  - `RUNNING` 卡住
  - `detail0 = 0`
  - `parse_failed`
  - `Cannot access memory`
  - `Remote doesn't know how to detach`

本 skill 特别针对：
- `ST-Link`
- `st-util`
- `skip_attach: true`
- mailbox 通过 GDB 读 SRAM

## Background

这份 skill 来自 `STM32F103C8T6 Bluepill GPIO bench` 的 cross-instrument 调试：
- `ESP32-JTAG + STM32F103` 整包可通过
- `ST-Link + STM32F103` 早期只在 mailbox verify 上失败
- 最终根因不是 DUT 连线，也不是 mailbox firmware 本身
- 根因是 `check_mailbox_verify` 在 `skip_attach` 的 `st-util` 会话里用了 `detach`
- 改成 `disconnect` 后，`UART/SPI/EXTI/ADC` 全部恢复通过

## Failure Classes To Separate

先把问题分成三类：

1. DUT / loopback 本身不通
- visual behavior 也不对
- ESP32-JTAG 下通常也会失败

2. mailbox firmware 逻辑不对
- visual behavior 正常
- mailbox 状态不合理
- 两种 instrument 下都失败，或者表现一致

3. ST-Link verify semantics 不对
- visual behavior 正常
- 另一个 instrument 路径能过
- ST-Link 只在 verify/read 阶段异常
- 错误文本带有明显 `st-util` / GDB 语义痕迹

## Required Observations

至少收集：
- `result.json`
- `artifacts/mailbox_verify.json`
- `verify.log`
- `flash.log`
- 手工 GDB 读取结果
- 对照 instrument 的通过结果
- 必要时的 visual behavior（例如 LED）

重点看：
- `status`
- `detail0`
- `parse_failed`
- `Cannot access memory`
- `Remote doesn't know how to detach`
- `Protocol error with Rcmd: 00`

## Diagnosis Workflow

1. 先确认 build / flash 是否成功。
   - 如果 flash 都没成功，不要先分析 mailbox 语义
2. 做一个最小 visual-only 对照。
   - 例如让 LED 用慢闪 / 快闪表示回环结果
   - 用它判断 DUT loopback 本身是否成立
3. 用另一种 instrument 做对照。
   - 如果同一 firmware/test 在另一种 instrument 下通过，优先怀疑 verify semantics
4. 手工读 mailbox。
   - 如果手工 GDB 读也异常，说明不是 AEL 结果拼装问题
5. 看错误模式。
   - `RUNNING/0` 倾向于状态没有被正确读到或目标状态被扰动
   - `parse_failed + Cannot access memory + Remote doesn't know how to detach` 强烈指向 `st-util` 会话语义
6. 检查 `check_mailbox_verify` 的会话结束命令。
   - `skip_attach=true` 时不要默认继续用 `detach`
   - 对 `st-util` 更合适的是 `disconnect`

## Fix Pattern

在 `check_mailbox_verify` 中：
- 若 `skip_attach = false`
  - 保持 `detach`
- 若 `skip_attach = true`
  - 使用 `disconnect`

原因：
- `skip_attach` 会话通常对应 `st-util` / 非 BMDA 服务器
- 这类会话不一定支持 `detach` 语义
- `disconnect` 更符合现有 `st-util` 行为

## Validation Flow

1. 先只回归一个最高信号的单项。
   - 本次是 `UART mailbox`
2. 如果单项通过，再回归同类单项。
   - `SPI`
   - `EXTI`
3. 再回归完整 pack。
4. 更新 closeout，把“原先的错误判断”和“最终根因”写清楚。

## Evidence Pattern From This Case

高信号证据链：
- `STM32F103 UART` visual LED slow blink
  - 说明 loopback 本身是好的
- `ESP32-JTAG + STM32F103` 同一 mailbox test 通过
  - 说明 firmware / wiring 大方向是好的
- `ST-Link` 路径读到：
  - `parse_failed`
  - `Cannot access memory at address ...`
  - `Remote doesn't know how to detach`
- 改 `detach -> disconnect` 后 `ST-Link` 通过

## Common Pitfalls

- 太早怀疑 DUT 连线
- 太早重写 mailbox firmware
- 把 `st-util` 的会话语义当成 BMDA 一样处理
- 没先做 visual-only 对照
- 没用另一种 instrument 做交叉验证

## Recommended Output Shape

当再次遇到类似问题时，结论应按以下顺序输出：
- 现象
- 证据
- 已排除项
- 最可能根因
- 最小修复
- 回归结果

## Current Known Conclusion

对于 `ST-Link + st-util + skip_attach mailbox_verify`：
- `disconnect` 和 `detach` 不能混用
- 如果看到 `parse_failed` / `Cannot access memory` / `Remote doesn't know how to detach`
  应优先检查会话结束语义，而不是先怀疑 DUT 行为
