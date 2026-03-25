# AEL Artifact Classification Rules v1
# When AEL generates outputs, where do they belong?

Applies to: docs, specs, guides, skills, tests, patterns, configs, experiments.
Derived from: ESP32JTAG brownfield migration, 2026-03-24 (first real case).

---

## The Three Layers

```
Layer 3: AEL-Core          ← most abstract, board-independent
Layer 2: Family/Platform   ← ESP32, STM32, RISC-V, etc.
Layer 1: Board/Project     ← this specific board/firmware only
Not Persisted              ← session noise, ephemeral state
```

---

## Decision Rules (in order — stop at first match)

### Rule 1 — Board-specific (Layer 1)

**Trigger:** the output depends on any of:
- This board's specific FPGA, logic analyzer, or port routing
- This board's physical wiring or loopback connections
- This board's USB VID/PID, serial number, or port path
- This board's firmware binary format or REST API endpoints
- This board's boot log patterns (specific log strings)
- This board's IP address or network configuration
- This board's sdkconfig or flash address offsets

**Examples:**
- `configs/boards/esp32jtag_instrument_s3.yaml` — USB VID, serial, boot patterns
- `tests/plans/esp32jtag_firmware_smoke.json` — specific boot patterns, USB serial
- `experiments/esp32jtag/port_d_loopback.py` — P3→P0 wiring, FPGA counter API
- `ael/instruments/interfaces/esp32jtag.py` — ESP32JTAG REST API protocol

**Storage:** `configs/boards/`, `tests/plans/`, `packs/`, `experiments/<board>/`,
`projects/<board>/`, `ael/instruments/interfaces/`, `docs/skills/`, `docs/checklists/`

---

### Rule 2 — Family/Platform-Specific (Layer 2)

**Trigger:** the output applies to ALL boards of a family but NOT to every possible system. Typical signals:
- Mentions specific SDK/toolchain (ESP-IDF, STM32CubeIDE, Zephyr)
- Applies to a chip family (ESP32-S3, STM32F4, RP2040)
- Covers an OS-level behavior common to that platform (USB CDC baud behavior, RTS/DTR)
- Describes migration patterns for one class of project

**Test:** Would this help me migrate a DIFFERENT ESP32-S3 board tomorrow? If yes → Layer 2.

**Examples:**
- `docs/specs/brownfield_firmware_onboarding_spec_v0_1.md` — ESP32 USB type classification
- `docs/guides/brownfield_migration_checklist.md` — ESP32/IDF brownfield checklist
- `docs/specs/esp32_family_brownfield_migration_guide_v1.md` — this migration family guide
- `ael/adapters/build_idf.py` — ESP-IDF build adapter
- CE record `7daa8c80` — ESP32 USB interface classification

**Storage:** `docs/specs/` (family prefix), `docs/guides/`, `ael/adapters/`,
Civilization Engine (`scope='board_family'`), Memory (`feedback_*.md`, `reference_*.md`)

---

### Rule 3 — AEL-Core (Layer 3)

**Trigger:** the output describes a method or pattern that applies to ANY system,
regardless of MCU, OS, SDK, or board. Could apply to STM32, ESP32, FPGA, Linux equally.

**Test:** Does removing all MCU/board/SDK names leave the content still valid? If yes → Layer 3.

**Examples:**
- `docs/specs/ael_universal_bringup_spec_v1.md` — Discovery → ... → Explore method
- `docs/specs/ael_artifact_classification_rules_v1.md` — this document
- `ael/patterns/loopback/pcnt_loopback.py` — pure firmware, no board hardware required
- Build → Deploy → Observe → Verify loop concept

**Storage:** `docs/specs/` (ael_ prefix), `ael/patterns/` (with generic callables),
Civilization Engine (`scope='pattern'` + `[HIGH_PRIORITY]`)

---

### Rule 4 — Not Persisted

**Trigger:** any of:
- Session debugging output (error traces, ad-hoc observations during development)
- Reasoning steps taken during a conversation (why this approach, alternatives considered)
- Intermediate notes that duplicate content already captured in permanent artifacts
- Code fragments or test results that are already represented in committed files
- Design memos created to align thinking during a session, superseded by final specs

**Examples:**
- Design memos dated during a session (e.g., `esp32jtag_interface_gap_matrix_2026-03-19.md`)
- `onboarding_notes.md` when all facts are already in `project.yaml`
- Inline debugging print output
- Multiple draft versions of a spec (keep final, discard drafts)

**Action:** Do not create. If already created, move to `docs/specs/archive/` or delete.

---

## Application: Borderline Cases

### "Is this pattern board-specific or AEL-core?"

Ask: **what are the dependencies?**

```
la_loopback_validation.py:
  - Depends on: binary format (ESP32JTAG /instant_capture protocol)
  - But: callable interface (output_fn, capture_fn) is generic
  → Classify as: conditionally reusable (Layer 2/3 boundary)
  → Action: keep in ael/patterns/, document the binary format dependency explicitly

pcnt_loopback.py:
  - Depends on: firmware can measure pulses (any MCU with PCNT or equivalent)
  - No board hardware required (1 jumper wire)
  → Classify as: AEL-core (Layer 3)
```

### "Is this ESP32-specific or AEL-core?"

```
baud=null handling:
  - Affects: all USB CDC devices (ESP32, RP2040, STM32 CDC)
  - But: primarily triggered by ESP32 USB architecture
  → Classify as: Family (Layer 2), keep in ESP32 guide
  → Note in AEL-core spec as a "platform quirk" category, not the fix itself

skip_set_target:
  - Only exists in ESP-IDF
  → Classify as: Family (Layer 2)

manual BOOT+RESET recovery:
  - Specific to Espressif native USB architecture
  → Classify as: Family (Layer 2), with note that it's ESP32-specific behavior
```

### "Is this a new AEL-core insight or just a board fact?"

```
"DHCP IPs are not stable identifiers" — applies to any WiFi device on any platform
→ Layer 3 observation, mention in ael_universal_bringup_spec

"FPGA configured OK - status = 0 is the FPGA ready signal" — specific to ESP32JTAG firmware
→ Layer 1, stays in project.yaml confirmed_facts and smoke test plan
```

---

## Summary Table

| Question | If YES → |
|----------|----------|
| Depends on this board's FPGA/LA/wiring/API? | Layer 1 (board) |
| Only valid for this board's USB VID/serial/IP? | Layer 1 (board) |
| Applies to any ESP32 / ESP-IDF project? | Layer 2 (family) |
| Applies to any STM32 / Zephyr / IDF project of this class? | Layer 2 (family) |
| Valid for any MCU/board, strip all names, still true? | Layer 3 (core) |
| Session artifact, debugging noise, superseded draft? | Not persisted |

---

## Storage Location Quick Reference

| Layer | Primary Locations |
|-------|-----------------|
| Board (1) | `configs/boards/`, `tests/plans/`, `packs/`, `experiments/<board>/`, `projects/<board>/`, `ael/instruments/interfaces/`, `docs/skills/<board>_*.md` |
| Family (2) | `docs/specs/<family>_*.md`, `docs/guides/<family>_*.md`, `ael/adapters/`, CE `scope='board_family'` |
| Core (3) | `docs/specs/ael_*.md`, `ael/patterns/` (generic callables), CE `scope='pattern'` |
| Not persisted | `docs/specs/archive/` if needed for reference, otherwise delete |
