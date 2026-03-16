# Spec: New Board Bring-Up Sequence v0.1

## Status
Adopted — validated on STM32G431CBU6 hardware (2026-03-16), 9/9 tests PASS.

---

## Purpose

Define the standard four-step hardware bring-up sequence for any new MCU board.

This sequence is the result of the STM32G431CBU6 experience, where a layered approach — starting with a debug-path-only gate, then wiring, then GPIO sanity, then full peripherals — consistently surfaced root causes at the right layer and avoided wasted effort.

It is now the default starting point for any new board, not an optional enhancement.

---

## The Sequence

```
New board arrives
  │
  ├─ Step 0: minimal_runtime_mailbox          ← SWD / boot gate
  │    Pass criteria: magic OK, status=PASS, detail0 increments
  │    Proves: flash works, MCU boots, RAM writable, SWD readable
  │    Required before anything else is attempted.
  │
  ├─ Step 1: wiring / observe-map verification ← physical reality check
  │    Proves: bench wiring matches firmware pin assumptions
  │    Method: frequency-coded parallel scan (Method B preferred)
  │            or one-wire-at-a-time scan (Method A fallback)
  │    Output: confirmed observe_map in board config
  │
  ├─ Step 2: pair-level GPIO sanity            ← logic-level sanity
  │    Proves: each MCU pin is independently drivable and readable
  │    Does not require loopback wiring
  │    Catches: GPIO clock disabled, MODER misconfiguration, etc.
  │
  └─ Step 3: full smoke pack                   ← peripheral tests
       UART loopback, SPI, ADC, timer capture, EXTI, GPIO loopback, PWM
       Only reached after Steps 0–2 have passed.
```

---

## Why This Order

### Step 0 first — always

Every other test assumes:
- the board can be flashed and reset
- the MCU boots and runs code
- the SWD debug path is reliable
- the result reporting path (mailbox) works

None of the 8 peripheral tests verify those assumptions. If the board silently fails to boot, every peripheral test will fail for the same root cause — and no targeted evidence will point to it.

`minimal_runtime_mailbox` makes that root cause testable in isolation, with zero peripheral dependencies.

### Step 1 before signal tests

Peripheral tests fail silently if wiring is wrong. A UART loopback test that never sees a signal looks the same as a UART peripheral that never fires. Confirming wiring before any peripheral test prevents that ambiguity.

### Step 2 before peripheral tests

Peripheral failures can have many causes (peripheral init, clock, wiring, firmware logic). If the underlying GPIO is broken, all peripheral tests that use it will fail for the same root cause. Step 2 isolates that layer.

### Step 3 after the others

By the time peripheral tests run, flash/boot/SWD/wiring/GPIO layers are already confirmed. A failure in Step 3 is diagnostic: it is in the peripheral init, not in the infrastructure.

---

## Step 0 Details: minimal_runtime_mailbox

**Firmware target:** `firmware/targets/stm32g431_minimal_runtime_mailbox/`

**Test plan:** `tests/plans/stm32g431_minimal_runtime_mailbox.json`

**What it does:**
1. Writes magic + STATUS_RUNNING to mailbox at `AEL_MAILBOX_ADDR`
2. Runs minimal self-check (basic arithmetic, constant read)
3. On pass: writes STATUS_PASS, loops incrementing `detail0`
4. On fail: writes error_code + STATUS_FAIL, spins

**What to read:**
```bash
python3 tools/read_mailbox.py --ip 192.168.2.62
# or via AEL pipeline: check.mailbox_verify step
```

**Pass criteria:**

| Field | Expected |
|---|---|
| `magic` | `0xAE100001` |
| `status` | `2` (STATUS_PASS) |
| `error_code` | `0x00000000` |
| `detail0` | non-zero; increases between reads |

**Failure → next action:**

| Symptom | Likely cause |
|---|---|
| GDB cannot attach | SWD wiring or power problem |
| `magic` = 0x00000000 or 0xFFFFFFFF | MCU did not reach `main()` |
| `magic` correct, `status` = 1 after 10s | Self-check hanging |
| `magic` correct, `status` = 3 | Self-check detected error; read `error_code` |
| `detail0` does not change | MCU halted after writing status |

---

## Step 1 Details: Wiring / Observe-Map Verification

**Reference:** `docs/specs/bench_wiring_auto_discovery_spec_v0_1.md`

**Method B (preferred):** all MCU output pins drive distinct frequency-coded signals simultaneously. LA captures all channels in one shot. Frequency → pin identity is inferred from the frequency table.

**Output:** confirmed `observe_map` entries in the board config YAML, e.g.:
```yaml
observe_map:
  pa2: "P0.3"
  pa3: "P0.0"
  pa4: "P0.2"
  pb3: "P0.1"
```

---

## Step 2 Details: Pair-Level GPIO Sanity

Drive each MCU output pin individually, sense it with a loopback or LA, verify level matches. Catches misconfigured MODER, disabled peripheral clock, floating pins.

Not a functional peripheral test — just confirms each pin is independently controllable.

---

## Step 3 Details: Full Smoke Pack

Once Steps 0–2 pass, run the full smoke pack:

```bash
python3 -m ael pack --pack packs/smoke_stm32g431.json
```

The pack includes `minimal_runtime_mailbox` as test 0, so it also re-gates the boot path at the start of each full run.

---

## Applicability

This sequence applies to any board where:
- SWD or JTAG debug access is available
- RAM is writable by firmware
- `read_mailbox.py` or equivalent can read target memory

The exact firmware and test plans are MCU-family-specific. The sequence itself is universal.

---

## Evidence

This sequence was fully validated on 2026-03-16:
- STM32G431CBU6 9/9 tests PASS on first complete run
- `minimal_runtime_mailbox` passed as Step 0 in the pipeline
- `check.mailbox_verify` stage reads SWD result into run artifacts

Previous sequence (before Step 0 existed): 6/8 PASS on first run, with SPI and ADC requiring root cause investigation before passing. Step 0 would have confirmed the boot path immediately, isolating SPI/ADC as peripheral-layer issues from the start.
