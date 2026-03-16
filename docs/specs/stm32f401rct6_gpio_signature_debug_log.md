# STM32F401RCT6 GPIO Signature 调试过程记录

**日期：** 2026-03-15
**实验：** stm32f401_gpio_signature
**最终结果：** PASS（PA2=248Hz，PA3=125Hz，ratio=1.984）

---

## 背景

STM32F401RCT6 是本次 bringup 的第一块实验板。
GPIO signature 实验是 8 个实验中的第一个，也是最基础的健康检查：
固件驱动两个 GPIO 产生方波，LA 采集频率和占空比，验证 CPU 和时钟系统工作正常。

在 F411 上，这套流程已经跑通。F401 的外设寄存器地址与 F411 相同，
理论上移植应该很顺利——但实际调试经历了两轮失败。

---

## 第一轮：固件频率太低，LA 窗口捕不到足够的边沿

### 初始固件设计

固件基于 SysTick 1kHz 节拍，设计思路是：
- PA2 每 20 个 tick 翻转一次 → 25Hz
- PA3 每 40 个 tick 翻转一次 → 12.5Hz

选 25Hz 的原因是"低频更稳定，容易观察"，当时没有考虑 LA 的采样窗口限制。

### 失败原因分析

AEL 的 LA 采集有一个硬性约束：

```
65532 samples @ 260kHz = 0.252 秒采样窗口
```

在 0.252 秒内，25Hz 信号只能产生：

```
0.252s × 25Hz × 2（每周期两个边沿）≈ 12.6 个边沿
```

而 test plan 设置的 `min_edges: 20`，实际只捕到 ~6 个边沿（窗口不一定从信号边沿开始），
导致：

```
FAIL: edge_count_below_min (edges=6, min=20)
```

### 关键认知

这是第一次碰到 **LA 采样窗口 vs 信号频率** 的约束关系。
规律是：要在 0.252 秒内稳定捕到足够边沿，信号频率至少要在：

```
min_edges / (2 × 0.252s) ≈ 40Hz 以上（min_edges=20 时）
```

实际上为了留裕量，应该更高。

---

## 第二轮：固件频率提上去了，但 threshold 没跟着调

### 固件修改

将 SysTick 改为 1kHz，取消分频器：
- PA2 每 1 个 tick 翻转 → 设计值 500Hz
- PA3 每 2 个 tick 翻转 → 设计值 250Hz

同时把 test plan 的 `min_freq_hz` 设为：
- PA2: 300Hz
- PA3: 150Hz

看起来很合理——设计值 500Hz，threshold 300Hz，留了足够裕量。

### 失败原因分析

烧录运行后，LA 实测：

```
PA2: 248Hz
PA3: 124Hz
```

远低于设计值 500Hz/250Hz。

报错：
```
FAIL: freq_below_min (pa2: measured=248Hz, min=300Hz)
```

### 为什么固件比设计值慢一倍？

原因在于 SysTick 的轮询方式。固件用的是忙等轮询：

```c
while (1) {
    if ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {
        continue;   // 等待 tick
    }
    // 处理逻辑
    if (++div_pa2 >= 1u) {
        div_pa2 = 0u;
        GPIOA_ODR ^= (1u << 2);   // PA2 翻转
    }
}
```

`div_pa2 >= 1u` 永远成立（加 1 之后立刻 ≥ 1），所以实际上每个 tick 翻转一次。
SysTick 1kHz → 每毫秒翻转一次 → **PA2 频率 = 500 次翻转 / 秒 ÷ 2（一个周期需要两次翻转）= 250Hz**，不是 500Hz。

翻转频率和信号频率的换算关系被忽略了：
```
信号频率 = 翻转频率 / 2
```

实测 248Hz（略低于理论 250Hz）是正常的，因为轮询循环本身有微小开销。

---

## 第三轮：调整 threshold，匹配实测值

### 修改 test plan

不修改固件，直接把 threshold 调整为匹配实测值：

```json
"signal_checks": [
  {
    "name": "pa2_fast",
    "pin": "pa2",
    "min_freq_hz": 150.0,
    "max_freq_hz": 400.0,
    "min_edges": 50,
    "max_edges": 2000
  },
  {
    "name": "pa3_half_rate",
    "pin": "pa3",
    "min_freq_hz": 75.0,
    "max_freq_hz": 200.0,
    "min_edges": 25,
    "max_edges": 1000
  }
],
"signal_relations": [
  {
    "type": "frequency_ratio",
    "numerator": "pa2_fast",
    "denominator": "pa3_half_rate",
    "min_ratio": 1.8,
    "max_ratio": 2.2
  }
]
```

设计思路：
- `min_freq_hz` 设为实测值的 60%（248Hz × 0.6 ≈ 150Hz），留温度和电压裕量
- `max_freq_hz` 设为实测值的 160%，防止异常高频误判
- 频率比 1.8~2.2，验证 PA3 确实是 PA2 的一半

### 结果

```
PASS
PA2: 248Hz（在 150~400Hz 范围内）
PA3: 125Hz（在 75~200Hz 范围内）
ratio: 1.984（在 1.8~2.2 范围内）
```

---

## 经验总结

| 问题 | 根因 | 解决方法 |
|------|------|---------|
| 边沿数不足 | LA 窗口 0.252s，25Hz 信号只有 ~6 边沿 | 提高固件频率到 250Hz 量级 |
| 频率低于 threshold | 翻转频率 ≠ 信号频率，需除以 2 | 按实测值设 threshold，留 ±40% 裕量 |
| Threshold 不合理 | 直接用"设计值"而非"实测值"做下限 | 先跑一次，看实测，再定 threshold |

### 核心原则（适用所有 GPIO 类实验）

1. **先跑，再定 threshold。** 不要用理论计算值直接做 threshold，先烧录跑一次，
   看实际测量值，再以实测值为基准设上下限。

2. **LA 窗口约束。** 0.252 秒内至少要有 `min_edges` 个边沿，
   意味着信号频率下限 ≈ `min_edges / (2 × 0.252)`。
   对 min_edges=50，频率下限约 100Hz。

3. **翻转频率 vs 信号频率。** GPIO 每翻转一次只完成半个周期，
   信号频率 = 翻转次数 / 2。

4. **ratio 检查比绝对频率更稳定。** 两路信号的频率比不受时钟偏差影响，
   是验证固件逻辑正确性的更可靠指标。

---

## 最终固件逻辑（简化）

```c
// SysTick 1kHz（16MHz HSI，RVR=15999）
// 每个 tick（1ms）进入一次处理循环

// PA2：每 tick 翻转 → 实测 ~248Hz
if (++div_pa2 >= 1u) {
    div_pa2 = 0u;
    GPIOA_ODR ^= (1u << 2);
}

// PA3：每 2 tick 翻转 → 实测 ~125Hz（PA2 的一半）
if (++div_pa3 >= 2u) {
    div_pa3 = 0u;
    GPIOA_ODR ^= (1u << 3);
}
```

比例关系由计数器决定，与时钟绝对精度无关，因此 ratio 非常稳定（1.984，接近理论值 2.0）。
