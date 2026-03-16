# STM32F401RCT6 完整 Bringup 过程记录

**日期：** 2026-03-15
**最终结果：** 8 / 8 实验全部 PASS，已 promote 为 verified board
**参考实现：** STM32F411CEU6（同一 F4 外设寄存器地址，移植基础）

---

## 一、背景与目标

STM32F401RCT6 是 AEL 的第二块 STM32F4 参考板，目标是完整复刻 F411 的 8 实验套件：

| # | 实验 | 验证内容 |
|---|------|---------|
| 1 | GPIO signature | CPU + 时钟系统基础健康 |
| 2 | UART loopback banner | USART1 收发 |
| 3 | SPI banner | SPI2 全双工收发 |
| 4 | ADC banner | ADC1 模拟采样 |
| 5 | TIM capture banner | TIM1→TIM3 输入捕获 |
| 6 | EXTI banner | 外部中断计数 |
| 7 | GPIO loopback banner | GPIO 输出→输入读回 |
| 8 | PWM banner | TIM1 PWM 输出 |

决策依据：F401 和 F411 使用相同的 F4 外设寄存器映射，
SPI2 / USART1 / TIM1 / TIM3 / ADC1 引脚分配完全一致，
可以直接移植固件，只需更换头文件。

---

## 二、准备阶段：连线与 Board Config

### 2.1 初始连线设计

第一版连线表遗漏了 SPI SCK（PB13）：

```
PA2  → P0.0   主状态信号
PA3  → P0.1   辅助签名（半频）
PC13 → LED    心跳 LED
```

用户审查后指出 PB13 缺失。

### 2.2 问题：SPI SCK 未连到 Instrument

**现象：** 用户指出连线表里没有 SPI SCK。

**根因：** 初始设计只考虑了"状态观测"引脚（PA2/PA3），
没有把辅助观测引脚（SPI SCK）纳入连线表。

**修复：** 在 board config 和 DUT docs 里补加 PB13 → P0.2。

**最终连线表：**

| DUT pin | Instrument (ESP32JTAG) | 角色 |
|---------|------------------------|------|
| PA2 | P0.0 | 主状态 / signature 信号 |
| PA3 | P0.1 | 辅助 signature（半频） |
| PB13 | P0.2 | SPI2 SCK 辅助观测 |
| PC13 | LED | 心跳 LED |
| GND | probe GND | 公共地 |
| SWDIO/SWDCLK | P3 | SWD 调试/烧录 |

**经验：** 连线表初稿完成后，需要逐一对应实验中每个外设的关键信号，
确认所有需要观测的引脚都已连线，不能只考虑状态输出引脚。

### 2.3 Board-side Loopback

所有板上短接线在实验开始前**一次性全部接好**，8 个实验全程使用同一套物理接线，
中间没有任何换线操作：

| 短接线 | 用于实验 |
|--------|---------|
| PA9 → PA10 | UART loopback |
| PB15 → PB14 | SPI |
| PB1 → PB0 | ADC |
| PA8 → PA6 | Capture、EXTI、GPIO loopback、PWM |

**重要原则：** bench 连线是一次性设置，不是按实验切换的。
设计实验套件时，应确保所有实验的连线需求可以同时满足，
让用户接好一次后直接跑完整套。

---

## 三、固件准备：Linker Script 修复

### 3.1 问题：`_sidata` undefined reference

将 7 个 banner 固件目录建好后，第一次全量编译，所有 7 个目标全部报同一个错误：

```
undefined reference to `_sidata'
```

**根因：** `startup_stm32f401xc.s`（CMSIS 官方启动文件）在 `.data` 段初始化时
引用了符号 `_sidata`（源数据在 Flash 中的加载地址），但 linker script 没有定义这个符号。

对比 F411 的 linker script：F411 版本在 `.data` 段前用 `AT` 语法显式指定加载地址，
不需要 `_sidata`；F401 的 CMSIS 启动文件版本不同，要求 linker 提供这个符号。

**修复：** 在 `stm32f401.ld` 的 `.data` 段开头加一行：

```ld
.data :
{
    _sidata = LOADADDR(.data);   ← 新增这一行
    _sdata = .;
    *(.data*)
    _edata = .;
} > RAM AT > FLASH
```

`LOADADDR(.data)` 是 GNU ld 的内置函数，返回该段在 Flash 中的加载地址，
正好就是 `_sidata` 需要的值。

**影响：** 这一修复让所有 7 个 banner 固件目录同时通过编译。
因为所有 banner 固件共用同一个 linker script（`../stm32f401rct6/stm32f401.ld`），
一次修复覆盖全部。

**经验：** 不同版本的 CMSIS 启动文件对 linker script 的符号要求不同。
从其他板移植时，不能直接复用 linker script，需要对照启动文件检查所有外部符号引用。

---

## 四、实验 1/8：GPIO Signature 三轮调试

（详细过程见 `stm32f401rct6_gpio_signature_debug_log.md`，此处仅列摘要）

### 第一轮失败：边沿数不足

- 固件：PA2 25Hz，PA3 12.5Hz
- 问题：LA 窗口 0.252s × 25Hz ≈ 6 边沿 < min_edges:20
- 结论：频率太低，LA 窗口捕不够

### 第二轮失败：threshold 高于实测值

- 固件：PA2 设计值 500Hz（每 tick 翻转）
- 问题：实测 248Hz（翻转频率 ÷ 2 = 信号频率，再加轮询开销）
- threshold min_freq_hz:300 > 实测 248Hz → FAIL

### 第三轮 PASS

- threshold 调整为实测值基础上 ×0.6 / ×1.6
- min_freq_hz: 150（PA2）/ 75（PA3）
- 加 signal_relations ratio 检查（1.8~2.2）
- 实测：PA2=248Hz，PA3=125Hz，ratio=1.984 → **PASS**

---

## 五、实验 2–4：UART / SPI / ADC（首跑即通）

### 实验 2/8：UART loopback banner

- 连线：PA9 → PA10（板上短接）
- 固件：USART1 发送测试字节，读回比对，结果输出到 PA2
- 结果：**PASS（首跑）**

### 实验 3/8：SPI banner

- 连线：PB15 → PB14（板上短接）；PB13 已连 P0.2
- 固件：SPI2 全双工收发，自比对，结果输出到 PA2
- 结果：**PASS（首跑）**

### 实验 4/8：ADC banner

- 连线：PB1 → PB0（板上短接）
- 固件：ADC1_IN8(PB0) 采样，与 PB1 驱动电平比对，结果输出到 PA2
- 结果：**PASS（首跑）**

这三个实验能首跑即通，关键因素是 F401 与 F411 外设寄存器完全一致，
移植只改了 `#include "stm32f411xe.h"` → `#include "stm32f401xc.h"`。

---

## 六、实验 5–8：Capture / EXTI / GPIO loopback / PWM

这四个实验共用 **PA8 → PA6** 板上短接线，用户接好一次后连续跑完。

### 实验 5/8：TIM capture banner

- 固件：TIM1 CH1 从 PA8 输出方波，TIM3 CH1 从 PA6 捕获，比对频率，结果输出 PA2
- 结果：**PASS（首跑）**

### 实验 6/8：EXTI banner

- 固件：PA8 输出脉冲，PA6 接 EXTI6 中断，计数边沿，与预期比对，结果输出 PA2
- 结果：**PASS（首跑）**

### 实验 7/8：GPIO loopback banner

- 固件：PA8 输出高/低，PA6 读回，比对电平，结果输出 PA2
- 结果：**PASS（首跑）**

### 实验 8/8：PWM banner

- 固件：TIM1 CH1 PA8 输出 PWM，PA6 读取占空比，与预期比对，结果输出 PA2
- 结果：**PASS（首跑）**

---

## 七、全套连续跑：8/8 PASS

所有实验单独通过后，做了一次完整的顺序连续跑：

```
experiments 1–4：无额外短接（各自独立接线）
experiments 5–8：PA8 → PA6 短接保持
```

结果：**8/8 PASS，无失败，无重跑。**

随后又做了 10 轮 × 4 板的 default verification 连续重复，40/40 PASS，零失败，
证明稳定性达到 reference 级别。

---

## 八、Promote 流程

| 步骤 | 内容 |
|------|------|
| manifest | 更新 `verified: true`，补加 `verification_suite`, `tests`, `sequential_pass`, `latest_run_id` |
| 板卡文档 | 新建 `docs/boards/stm32f401rct6.md` |
| README | 新增 Verified Boards catalog 小节 |
| git tag | `board/stm32f401rct6-verified` |
| default verification | 移除 STM32F103，加入 STM32F401RCT6 gpio_signature |

---

## 九、问题汇总

| # | 问题 | 阶段 | 根因 | 解决 |
|---|------|------|------|------|
| 1 | SPI SCK 连线缺失 | 准备 | 连线表只考虑状态观测引脚 | 补加 PB13→P0.2 |
| 2 | `_sidata` undefined reference | 编译 | CMSIS 启动文件版本差异 | linker script 加 `_sidata = LOADADDR(.data)` |
| 3 | GPIO signature 边沿数不足 | 实验1 | 25Hz 在 0.252s 窗口内边沿太少 | 固件改为 ~250Hz |
| 4 | GPIO signature freq_below_min | 实验1 | threshold 用设计值，实测值 = 设计值 ÷ 2 | threshold 按实测值重设 |

---

## 十、可提炼为 Skill 的经验（供审查）

以下经验在本次 bringup 中被实际触发，建议评估是否值得写成 Skill：

### S1：CMSIS Startup 符号检查 Skill（已有部分基础）
移植到新 MCU 前，grep startup 文件中所有外部符号引用，逐一确认 linker script 已定义。
命令：`grep -E "^\s+ldr|EXTERN|PROVIDE" startup_*.s`

### S2：连线完整性 Checklist Skill
每个实验的所有外设信号引脚（不只是状态输出）都应出现在连线表中。
实验开始前按 test plan 的 `bench_setup.peripheral_signals` 逐条核对。

### S3：Banner 实验 "结果输出" 模式 Skill
Banner 模式的核心是：固件内部自测完成，通过 PA2 的频率/占空比编码输出 PASS/FAIL。
只要 PA2 信号正常，就代表所有内部测试通过。这是一套可复用的固件架构模式。

### S4：GPIO Signal Threshold Skill（已完成）
见 `docs/skills/gpio_signal_threshold_skill.md`。
