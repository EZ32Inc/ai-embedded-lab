# Memo: GDB load 后目标不自动运行的问题与通用修复模式

**适用路径**: AEL `flash_bmda_gdbmi` 自定义 `gdb_launch_cmds` + `st-util` / 其他不自动 resume 的 GDB server
**首次发现**: STM32F407 Discovery + ST-Link 直接集成, 2026-03-17
**状态**: 已修复并验证

---

## 症状

- Flash 阶段：PASS（GDB 输出显示固件已写入，`load` 完成，exit code 0）
- mailbox 验证阶段：FAIL
- mailbox 读取内容：`magic_ok: true`，`status: RUNNING`，`detail0: 0`

`magic_ok: true` 说明 GDB 成功连接并读取了内存；但 `detail0: 0` 说明固件从未执行过任何循环迭代——**目标芯片处于 halted 状态**。

---

## 根因

GDB `--batch` 模式执行 `load` 后，芯片处于 halt 状态（PC 指向 reset handler，但未开始执行）。

`disconnect` 命令只是关闭 GDB 与 GDB server 的 TCP 连接，**不会向目标发送 resume 指令**。

不同 GDB server 对 disconnect 的行为不一致：

| GDB server | disconnect 后目标状态 |
|---|---|
| OpenOCD（默认配置） | 通常自动 resume |
| st-util（stlink 1.8.x） | 保持 halted |
| BMDA (Black Magic) | 取决于配置 |

因此，使用 st-util 时，如果 `gdb_launch_cmds` 只有 `load` + `disconnect`，固件永远不会运行。

---

## 修复方法

在 `load` 之后、`disconnect` 之前，添加 `monitor reset run`：

```yaml
gdb_launch_cmds:
  - "file {firmware}"
  - "load"
  - "monitor reset run"   # 通知 GDB server 复位并启动目标
  - "disconnect"
```

`monitor reset run` 是发给 GDB server 的 remote command，语义是"复位 MCU 并开始执行"。该命令立即返回（服务器异步处理），GDB 不需要等待目标停止，可以直接 `disconnect`。

---

## 为什么不用 `continue` + `disconnect`

`continue` 在 `--batch` 模式下会阻塞，等待目标产生停止事件（breakpoint 或 exception）。对于无限循环的裸机固件，GDB 进程会永久挂起，`disconnect` 永远不会执行。

`monitor reset run` + `disconnect` 是正确的无阻塞模式。

---

## 验证

修复后 `ael run` 输出：

```
Flash: attempt 1 (normal) -> OK
Flash: OK
Flash: settling 4.00s before next stage
PASS: Run verified
```

mailbox 读取内容：`status: PASS`，`detail0` 递增，符合预期。

---

## 适用范围与复用建议

任何通过 `gdb_launch_cmds` 自定义 flash 路径的 board config，**只要使用的 GDB server 不在 disconnect 时自动 resume**，都应加入 `monitor reset run`。

判断方法：flash 后 mailbox `detail0` 为 0 且 magic 有效 → 固件未运行 → 缺少 resume 指令。

如果目标 GDB server 不支持 `monitor reset run`（极少数情况），备选方案：
- `monitor reset` + `monitor run`（分两步）
- `set $pc = *0x08000004`（手动设置 PC 到 reset vector）然后 `continue &`（仅限支持异步模式的 GDB）

---

## Board-specific note: STM32F4 Discovery PA9/PA10 不适合 UART loopback

**发现时间**: STM32F407 smoke pack 开发过程中, 2026-03-17

### 症状

在 STM32F4 Discovery 上对 USART1 PA9(TX)→PA10(RX) 做自环测试，结果：
- mailbox magic 有效（固件在运行）
- error_code = 0x10（byte 0 接收超时）
- 重新插拔跳线后问题依然存在

### 根因

STM32F4 Discovery MB997D/E（搭载 ST-Link/V2-A）将 **PA9/PA10 连接到板载 ST-Link 的 UART 桥接电路**。ST-Link MCU 在 PA10 上存在干扰信号，导致 USART1 RX 永远收不到自己发出的字节。

### 修复

改用 **USART2 on PD5(TX) → PD6(RX)**，这两个引脚无任何板载连接：

```yaml
# tests/plans/stm32f407_uart_loopback.json
peripheral_signals:
  - role: USART2_TX  dut_signal: PD5
  - role: USART2_RX  dut_signal: PD6
```

```c
/* firmware: USART2, APB1, AF7 */
RCC_APB1ENR |= (1U << 17);   /* USART2EN */
GPIOD_MODER |= (0xAU << 10); /* PD5/PD6 AF mode */
GPIOD_AFRL  |= (0x77U << 20);/* PD5/PD6 = AF7 */
```

换引脚后立即 PASS，pack 5/5 稳定通过。

### 适用范围

仅影响 STM32F4 Discovery 板（MB997D/E 及类似版本）。其他 STM32 板上 PA9/PA10 通常是干净引脚，不受此限制。
