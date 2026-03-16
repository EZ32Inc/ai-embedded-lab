# Bench Wiring Completeness Skill

## Purpose

Ensure all required signals are physically connected before running an
experiment suite, by systematically cross-checking wiring against
test plan requirements.

Based on real incident: STM32F401RCT6 bringup (2026-03-15), SPI SCK
(PB13) was missing from the initial wiring table and required a
correction mid-session.

---

## Trigger

Use this skill whenever:

- Designing a wiring table for a new board
- Preparing a bench for a multi-experiment suite
- Reviewing a DUT's `docs.md` or `bench_connections` in board config
- Adding a new experiment to an existing board's suite

---

## Core Rules

### Rule 1: Wiring is set once for the entire suite

All bench connections — instrument wires AND board-side loopbacks —
are connected **before the first experiment runs** and stay unchanged
for the entire suite. Never assume wires will be changed between experiments.

Design the wiring table so that every experiment's requirements are
simultaneously satisfied by one physical setup.

### Rule 2: Cover all signal roles, not just status outputs

For each experiment in the suite, check its `bench_setup.peripheral_signals`
and verify that **every signal** appears in the wiring table:

- Status / verify output (e.g. PA2 → P0.0) — usually already there
- Peripheral clock signals (e.g. SPI SCK PB13 → P0.2) — easy to miss
- Board-side loopback wires (e.g. PA9 → PA10 for UART)
- Power / ground references

### Rule 3: Trace from test plan, not from memory

Do not rely on memory or analogy with other boards.
Always trace from the test plan's `bench_setup` → DUT signal → physical pin → instrument pin.

---

## How to Check

### Step 1: Collect all peripheral signals from test plans

For each test plan in the suite:

```bash
cat tests/plans/<board>_*.json | python3 -m json.tool \
  | grep -A3 "peripheral_signals\|dut_signal"
```

### Step 2: Build a signal inventory

List every unique DUT signal that appears across all test plans.

### Step 3: Cross-check against wiring table

Every signal in the inventory must appear in one of:
- `configs/boards/<board>.yaml` → `bench_connections`
- `assets_golden/duts/<board>/docs.md` → Bench Wiring table
- As a board-side loopback in the docs

### Step 4: Identify gaps

Any signal present in test plans but absent from wiring table = **missing connection**.
Add it before the session starts.

---

## Example: What Was Missed in F401 Bringup

Initial wiring table had:

```
PA2  → P0.0   ✓ (status signal)
PA3  → P0.1   ✓ (aux signature)
PC13 → LED    ✓ (heartbeat)
```

SPI banner test plan required:

```
PB13 (SPI2_SCK) → observation point
```

PB13 was in the test plan's `peripheral_signals` but absent from the
wiring table. Caught by user review, added as PB13 → P0.2.

---

## Checklist

- [ ] Collected all `peripheral_signals` from every test plan in the suite
- [ ] Built signal inventory (unique DUT pins required)
- [ ] Every inventory pin appears in wiring table or loopback list
- [ ] Wiring satisfies all experiments simultaneously (no mid-suite changes needed)
- [ ] Wiring table committed to `assets_golden/duts/<board>/docs.md` before first run
