# GPIO Signal Threshold Skill

## Purpose

Guide correct threshold setting for GPIO signal verification test plans,
based on real hardware debugging experience (STM32F401RCT6, 2026-03-15).

---

## Trigger

Use this skill whenever:

- Writing or reviewing a test plan with `signal_checks` (freq, duty, edge counts)
- Setting `min_freq_hz`, `max_freq_hz`, `min_edges`, `max_edges` for any GPIO signal
- Debugging a `freq_below_min` or `edge_count_below_min` failure

---

## Core Rules

### Rule 1: Run first, set threshold second

Never set `min_freq_hz` from a theoretical / design value alone.
Flash the firmware, run one capture, read the actual measured frequency,
then set the threshold based on the measured value with ±40% margin:

```
min_freq_hz = measured_hz × 0.6
max_freq_hz = measured_hz × 1.6
```

If no hardware is available yet, use a wide placeholder (e.g. 10–2000 Hz)
and tighten after the first real run.

---

### Rule 2: LA window constrains minimum signal frequency

The LA capture window is fixed:

```
65532 samples @ 260kHz = 0.252 seconds
```

To reliably capture `min_edges` edges in that window:

```
required_freq_hz > min_edges / (2 × 0.252s)
```

| min_edges | minimum signal frequency |
|-----------|--------------------------|
| 10        | ~20 Hz                   |
| 25        | ~50 Hz                   |
| 50        | ~100 Hz                  |
| 100       | ~200 Hz                  |

If the firmware frequency is too low, increase it — do not reduce `min_edges`
below the point where a single glitch could pass the check.

---

### Rule 3: Toggle frequency ≠ signal frequency

A GPIO toggling N times per second produces a signal at N/2 Hz:

```
signal_freq_hz = toggle_rate_hz / 2
```

Example: SysTick at 1kHz, toggle every tick → 1000 toggles/sec → **500 Hz signal**
But if each toggle takes the full 1ms tick → **500 Hz**... unless the loop
body adds latency, which typically reduces it to ~250 Hz in a polling loop.

**Always verify on hardware.** Polled SysTick loops consistently run slower
than the theoretical toggle rate due to loop overhead.

---

### Rule 4: Frequency ratio is more reliable than absolute frequency

Two signals driven from the same counter have a ratio that is immune to
clock drift, temperature, and voltage variation. Use `signal_relations`
with `type: frequency_ratio` to verify firmware logic correctness:

```json
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

A ratio check of 1.8–2.2 will pass even if absolute frequency drifts ±20%.

---

## Checklist Before Submitting a GPIO Test Plan

- [ ] `min_freq_hz` based on measured value, not design value
- [ ] `min_edges` consistent with LA window constraint (Rule 2)
- [ ] Toggle-to-frequency conversion verified (Rule 3)
- [ ] `signal_relations` ratio check added if two related signals exist
- [ ] At least one real hardware run done before finalizing thresholds
