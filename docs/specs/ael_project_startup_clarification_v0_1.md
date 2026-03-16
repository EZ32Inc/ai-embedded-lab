# AEL Real-Project Startup Clarification Spec v0.1

**Date:** 2026-03-16
**Status:** draft
**Problem it solves:** AI proceeds with repo-example assumptions that do not match the user's real setup.

---

## 1. Why Repo-Example Assumptions Are Dangerous

AEL contains growing knowledge of verified boards, instruments, and wiring setups.
This knowledge is valuable — but it creates a subtle failure mode:

> **AEL assumes the user's real setup matches the repo example.**

This assumption is often false.

### Real incident: STM32F401RCT6 SPI SCK (2026-03-15)

The initial wiring table for F401 was designed by analogy with F411.
It included PA2, PA3, PC13 — the status and signature pins.
It did not include PB13 (SPI2 SCK) — because the F411 template didn't emphasize it.

The user had to review the wiring table manually and point out the missing connection.

If the user had not caught this, the SPI experiment would have run without
the SCK pin connected to the instrument, and the result would have been
misleading (firmware may still report PASS via PA2 even if SCK is unobservable).

### The general pattern

| What AEL assumes | What may actually be true |
|-----------------|--------------------------|
| Same instrument as the reference board | Different instrument, different IP |
| Same pin connections as the reference | Different wiring, missing connections |
| Same loopback wires in place | No loopbacks, or different loopbacks |
| Board is a known dev board | Custom PCB with different pinout |
| Flash method works as configured | Different programmer, different interface |

Each of these mismatches can cause:
- Silent failures (test runs but verifies the wrong thing)
- Hard failures (preflight fails with confusing error)
- Wasted time debugging the wrong layer

---

## 2. The Behavior AEL Must Change

### Current (wrong) behavior

```
User: "Create a project for my STM32F411 board"

AEL: [looks up stm32f411ceu6 in known_boards.yaml]
     [finds mature path]
     [proceeds with bench_connections from board config]
     [assumes esp32jtag_stm32_golden at 192.168.2.98]
     [generates project with confirmed_facts copied from reference]
```

This is fast but fragile. It works only when the user's setup is identical
to the reference. In real projects, it frequently is not.

### Target (correct) behavior

```
User: "Create a project for my STM32F411 board"

AEL: [looks up stm32f411ceu6 — finds mature path]
     [shows user the known setup]
     [asks: does your real bench match this?]
     [captures any differences]
     [writes confirmed_facts from user's actual answers]
     [then proceeds]
```

This is slightly slower on the first run, but:
- Eliminates silent assumption mismatches
- Produces reliable confirmed_facts from the start
- Prevents the "confident but wrong" failure mode

---

## 3. Minimum Information to Confirm

Before AEL begins generation or verification for any project, the following
must be explicitly confirmed — not assumed from repo history.

### Category 1: Board identity

| Question | Why it matters |
|----------|---------------|
| What MCU or board exactly? | Header files, linker script, register map |
| Dev board or custom PCB? | Pin availability, default peripherals |
| Any hardware modifications? | Non-standard pin usage |

### Category 2: Flash / programming

| Question | Why it matters |
|----------|---------------|
| How is the board being programmed? | SWD, UART, USB DFU |
| What programmer/interface? | OpenOCD, BMDA, esptool |
| Is the programmer currently connected and working? | Catch connection issues before building firmware |

### Category 3: Instrument

| Question | Why it matters |
|----------|---------------|
| Which instrument instance? | IP address, port, capability |
| Is the instrument online right now? | Preflight will fail if not |
| Which instrument pins are connected to which DUT pins? | Defines what is observable |

### Category 4: Wiring

| Question | Why it matters |
|----------|---------------|
| Which DUT signals are connected to the instrument? | Observable vs unobservable signals |
| Are all required loopback wires in place? | Missing loopback = experiment cannot run |
| Is the wiring the same as the reference, or different? | Detect deviations before running |

### Category 5: Success criteria

| Question | Why it matters |
|----------|---------------|
| What does a passing result look like? | Threshold setting, signal interpretation |
| What is known vs unknown about this board? | Guides which experiments to run first |
| Are there any known hardware issues? | Avoid false debugging loops |

---

## 4. Clarification Workflow

### When to trigger

Trigger the clarification workflow when:
- A new project is being created (`ael project create`)
- The board is known but `confirmed_facts` are incomplete or missing
- The user's described setup differs from the repo reference in any way
- The instrument IP or instance is not confirmed reachable

### When NOT to trigger

Skip clarification when:
- All `confirmed_facts` are already populated and confirmed
- The user explicitly states "same setup as last time" and last run was recent
- Running a repeat/regression run on an already-validated project

### Workflow steps

```
Step 1: Load known board profile (if board is recognized)
        Show user the assumed setup in structured form:
        - instrument: <name> at <ip>
        - wiring: <table>
        - loopbacks: <list>

Step 2: Ask user to confirm or correct
        "Does your current bench match this? (yes / describe differences)"

Step 3: Capture differences
        For each item the user corrects, record the actual value.

Step 4: Validate completeness
        Check that all required facts for the target experiments are confirmed.
        Flag any gaps.

Step 5: Write confirmed_facts
        Write all confirmed information into projects/<name>/project.yaml
        under confirmed_facts, with source: user_confirmed.

Step 6: Proceed
        Run-gate will now have real confirmed_facts to evaluate against.
```

---

## 5. confirmed_facts Structure

Facts written by the intake workflow follow this structure in `project.yaml`:

```yaml
confirmed_facts:
  - key: instrument_instance
    value: esp32jtag_stm32_golden
    source: user_confirmed
    confirmed_at: "2026-03-16"

  - key: instrument_endpoint
    value: "192.168.2.98:4242"
    source: user_confirmed
    confirmed_at: "2026-03-16"

  - key: wiring_pa2_to_p0_0
    value: "confirmed"
    source: user_confirmed
    confirmed_at: "2026-03-16"

  - key: loopback_pa9_pa10
    value: "confirmed"
    source: user_confirmed
    confirmed_at: "2026-03-16"
```

Key naming convention:
- `instrument_*` — instrument identity and connectivity
- `wiring_<dut_pin>_to_<instrument_pin>` — physical connections
- `loopback_<pin1>_<pin2>` — board-side loopbacks
- `board_type` — dev board vs custom PCB

---

## 6. AEL Behavior When Information Is Incomplete

| Situation | AEL behavior |
|-----------|-------------|
| Board unknown, no confirmed_facts | Ask all Category 1–5 questions before proceeding |
| Board known, confirmed_facts empty | Show reference setup, ask user to confirm or correct |
| Board known, confirmed_facts partial | Show what is confirmed, ask only for missing items |
| Board known, confirmed_facts complete | Proceed directly, no clarification needed |
| User says "same as last time" | Check last run date; if recent (< 7 days), accept; if older, re-confirm instrument connectivity |

---

## 7. Relationship to Existing AEL Mechanisms

| Mechanism | Role |
|-----------|------|
| `project questions` command | Shows current confirmation state — input to this workflow |
| `project run-gate` | Evaluates confirmed_facts before running — consumer of this workflow's output |
| `confirm_before_generation_policy_v0_1.md` | Governs when to pause for confirmation during generation |
| `mcu_pin_verification_skill.md` | Pin-level verification step within this workflow |
| `bench_wiring_completeness_skill.md` | Wiring checklist used in Step 4 of this workflow |

---

## 8. Implementation: `ael project intake` Command

The command that implements this workflow:

```bash
python3 -m ael project intake --project <name>
```

Behavior:
1. Load project and board profile
2. Display current confirmed_facts and gaps
3. For each gap, prompt user with a specific question
4. Validate answer format and plausibility
5. Write confirmed facts to project.yaml
6. Show updated confirmation status

This command should be run:
- After `ael project create` for any new project
- Any time the user indicates the bench setup has changed
- Before running a new experiment type on an existing project

---

## 9. Open Items

- [ ] Implement `ael project intake` command
- [ ] Define canonical list of required confirmed_facts per experiment type
- [ ] Add intake step to `new_board_bringup_skill.md` as a required step 1
- [ ] Add re-confirmation trigger when instrument IP changes between sessions
