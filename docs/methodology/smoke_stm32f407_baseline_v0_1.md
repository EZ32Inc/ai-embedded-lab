# STM32F407 Discovery + STLinkInstrument Smoke Pack Baseline

---

## 1. Purpose（意义）

`smoke_stm32f407` 是 AEL 中第一个完整验证的 STM32 board-level validation pack。

它的目标不是演示功能，而是：

- 提供一个**可重复执行的回归基线**（regression baseline）
- 验证 STLinkInstrument 的真实可用性
- 覆盖 MCU 的关键功能路径（内部 + 外部）
- 作为后续 STM32 板子支持的**模板**（template）

---

## 2. Scope（覆盖范围）

当前 pack 包含 7 个测试：

| # | 测试               | 验证内容             | 接线     |
|---|--------------------|----------------------|----------|
| 1 | mailbox            | 基础运行 + mailbox PASS | 无      |
| 2 | timer_mailbox      | TIM3 中断执行        | 无       |
| 3 | gpio_loopback      | GPIO 输出→输入       | PB0→PB1  |
| 4 | uart_loopback      | USART2 TX→RX         | PD5→PD6  |
| 5 | exti_trigger       | 外部中断触发         | PB8→PB9  |
| 6 | adc_loopback       | 模拟输入读取         | PC0→PC1  |
| 7 | spi_loopback       | SPI2 MOSI→MISO       | PB15→PB14|

---

## 3. Bench Wiring（接线规范）

```
PB0  -> PB1    (GPIO loopback)
PD5  -> PD6    (USART2 TX->RX)
PB8  -> PB9    (EXTI trigger)
PC0  -> PC1    (ADC loopback)
PB15 -> PB14   (SPI2 MOSI->MISO)
```

说明：

- 所有 loopback 均为直接跳线（direct jumper wiring）
- 不涉及任何外部器件
- 接线属于 pack 的一部分，必须严格匹配

---

## 4. Execution Model（执行模型）

**推荐执行方式：**

```bash
python3 -m ael pack --pack packs/smoke_stm32f407.json --board stm32f407_discovery
```

> 注意：`--board stm32f407_discovery` 在使用 `ael pack` 子命令（非 `ael run --dut`）时为必需参数，用于选取正确的 instrument instance（`stlink_f407_discovery`）并禁用不适用的 preflight 检查。

**Pack 内测试顺序：**

pack 已按以下顺序排列，无需手动调整：

1. **无需接线**（mailbox、timer）— 可快速确认 flash/mailbox 路径健康
2. **需要接线**（gpio / uart / exti / adc / spi）— 需提前接好全部 5 根跳线

这个顺序可：

- 最小化人工等待
- 提高失败定位效率
- 保持执行 momentum

---

## 5. Critical Integration Rules（关键规则）

### Rule 1 — ST-Link run-state behavior

在 `st-util` 路径下：

- `load` 后 target **不会**自动运行
- `disconnect` **不会** resume execution

必须在 `gdb_launch_cmds` 中显式执行：

```
monitor reset run
```

否则：

- firmware 已写入但不执行
- mailbox 永远不会更新
- 导致假 FAIL（status=RUNNING，detail0=0）

该规则已固化在 `configs/boards/stm32f407_discovery.yaml` 的 `gdb_launch_cmds` 中。

---

### Rule 2 — Board-level pin conflict

在 STM32F4 Discovery（MB997D/E，ST-Link/V2-A）上：

- **PA9 / PA10 不适合 UART loopback**
- 板载 ST-Link UART bridge 电路占用 PA9/PA10，导致 PA10（RX）被干扰，byte 0 永久超时（error_code=0x10）

**解决方案：** 使用 `USART2 PD5(TX) → PD6(RX)`，这两个引脚无板载冲突。

---

### Rule 3 — SPI MISO 全零典型诊断

SPI loopback 中出现：

```
error_code = 0x20  (byte mismatch at index 0)
detail0    = 0x00  (received byte = 0x00)
```

强烈指示**物理连接问题**：

- 跳线未接好（PB15→PB14）
- 引脚接错
- 接触不良

而**不是** firmware bug。先检查跳线，再怀疑代码。

---

## 6. Validation Philosophy（验证理念）

该 pack 体现的是：

> **board-level validation，而非 MCU-level demo**

验证对象包括：

- firmware correctness
- instrument path（ST-Link → st-util → GDB → mailbox）
- board wiring（loopback 物理回路）
- real signal behavior（ADC 真实 count，SPI 真实字节回传）

---

## 7. Regression Baseline（回归基线地位）

该 pack 已满足：

- 7/7 PASS
- 全包重复运行稳定 PASS
- 覆盖核心外设路径
- 包含物理接线验证

因此定义为：

> **STM32F407 Discovery + STLinkInstrument 的官方回归基线**

新增 STM32F407 相关测试前，应先确保本 pack 完整 PASS。

---

## 8. Reusability（可复用性）

该 pack 可作为模板用于：

- STM32G431
- STM32H750
- 其他 STM32 板子

**迁移方法：**

1. 复制 pack 结构
2. 修改 board config（`configs/boards/`）
3. 调整引脚映射（firmware + test plans）
4. 更新 bench wiring（`bench_setup.peripheral_signals`）
5. 重新验证全包

---

## 9. Key Outcome（关键成果）

AEL 已从：

> *"可以 flash 一个程序"*

演进为：

> **"可以系统性验证一个 MCU + board + instrument 组合"**

---

## 10. One-line Summary

> `smoke_stm32f407` 是 AEL 的第一个完整 STM32 验证模板与回归基线。

---

*End of document — v0.1*
