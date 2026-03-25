# ESP32JTAG Migration Method Record v1
# AEL Universal Bring-up — Structured Retrospective

Date: 2026-03-24
Board: ESP32JTAG instrument firmware (ESP32-S3)
Method: Discovery → Hypothesis → Confirmation → Execution → Verify → Explore
Outcome: Full migration complete, 8/8 loopback PASS, Civilization Engine updated

---

## Part 1 — Migration Reconstruction

### Stage A — Discovery

Auto-discoverable facts from the project directory and connected hardware:

| Signal | Source | Value |
|--------|--------|-------|
| MCU family | `sdkconfig: CONFIG_IDF_TARGET_ESP32S3=y` | ESP32-S3 |
| Build system | `CMakeLists.txt` present, `idf.py` available | ESP-IDF CMake |
| USB architecture | `sdkconfig: CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y` | Native USB only (Type B) |
| USB identity | `lsusb`, `udevadm info /dev/ttyACM0` | VID=303a PID=1001 serial=3C:DC:75:5A:9A:FC |
| Flash layout | `build/flash_args` present | Multi-binary (bootloader + app + partitions + OTA) |
| External project | `project_dir` outside AEL tree | `/nvme1t/work/esp32jtag_firmware` |
| sdkconfig state | `git log -- sdkconfig` shows tuned/committed state | skip_set_target required |
| FPGA presence | `main/esp32jtag_common.h`, `la_src/` | FPGA with SPI interface, LA capability |
| Logic analyzer | `main/web/website.html`, `/instant_capture` endpoint | 264 MHz, 16-ch, firmware-served |
| Web API | `main/network/web_server.c`, HTTPS :443 | REST API for GPIO, flash, LA control |
| GDB server | `main/network/*.c`, port 4242 | Remote GDB over WiFi |
| WiFi mode | Serial boot log: `GOT ip event!!!`, DHCP | STA mode, BELL567 AP |
| Device role | Firmware serves as a probe, not a DUT | Instrument firmware |
| Brownfield status | Existing build artifacts, real git history | Brownfield — already worked manually |

Discovery is **complete without user involvement** at this stage.

---

### Stage B — Hypothesis

AEL's structured hypothesis before asking any questions:

```
HYPOTHESIS: ESP32JTAG Brownfield Migration

MCU / Platform:
  ESP32-S3, ESP-IDF CMake, external project at /nvme1t/work/esp32jtag_firmware

Build:
  idf.py build (CMake) — multi-binary with flash_args
  skip_set_target=true (tuned sdkconfig committed to git)
  idf_path injection may be needed if idf.py not in PATH

Deploy:
  esptool write_flash @build/flash_args
  auto_reset=false (native USB — no RTS/DTR)
  requires_running_firmware=true (download mode via USB JTAG stub)
  Recovery: manual BOOT+RESET if firmware dead

Observe:
  Primary: USB serial /dev/ttyACM0 (usb_serial_jtag, baud=null)
  Secondary: network (DHCP IP from serial log, TCP :4242)
  Console disappears on firmware crash (USB stack in firmware)

Verify:
  Serial log patterns: FPGA ready, GDB ready, WiFi up, [APP] Free memory
  Network: ping + TCP :4242

Special resources:
  FPGA: SPI-connected, logic analyzer, GPIO routing, loopback capability
  Web API: HTTPS :443 — GPIO control, LA capture, version endpoint

Migration risks:
  [HIGH] RTS/DTR reset attempt will fail (native USB) — must suppress
  [HIGH] baud=null must be handled correctly (USB CDC ignores baud)
  [MEDIUM] Console loss on crash — AEL cannot auto-recover
  [MEDIUM] DHCP IP not stable — extract from serial log, not hardcoded
  [LOW] idf_path may need injection if not in PATH
```

---

### Stage C — Confirmation

What AEL should ask the user — concise, recognition-based, not open-ended:

```
AEL Hypothesis Check — ESP32JTAG Firmware Onboarding

Based on project inspection I believe:

[1] This board has a SINGLE native USB port (no bridge chip).
    RTS/DTR reset will NOT work. Recovery requires manual BOOT+RESET.
    → Correct? [Y/n]

[2] The sdkconfig is tuned and committed to git.
    AEL will NOT run idf.py set-target (it would destroy it).
    → Correct? [Y/n]

[3] idf.py is available in PATH.
    → Correct, or provide path: ___

[4] This is instrument firmware, not a DUT.
    AEL will validate via serial log + network, not GPIO waveforms.
    → Correct? [Y/n]

[5] The FPGA on this board has a logic analyzer and GPIO routing.
    AEL can use Port D output → Port A capture as a loopback self-test
    once physical wires are connected (P3→P0, 4 wires).
    → Noted for later? [Y/n]
```

This takes < 2 minutes. All other facts are discovered automatically.

---

### Stage D — Execution

What AEL actually needed to do to take control:

**Config generation:**
- `configs/boards/esp32jtag_instrument_s3.yaml` — board/firmware config with:
  - `usb_interface_type: native_only`
  - `console.type: usb_serial_jtag`, `baud: null`, `rts_dtr_reset: false`, `loss_on_crash: true`
  - `flash.auto_reset: false`, `use_flash_args: true`
  - `build.skip_set_target: true`, `project_dir: /nvme1t/work/esp32jtag_firmware`
- `projects/esp32jtag_firmware_onboarding/project.yaml` — project metadata and confirmed facts

**Build integration:**
- External project, path injection, skip_set_target
- Artifact discovery via `build/flash_args`

**Deploy integration:**
- `idf_esptool` runner using `write_flash @build/flash_args`
- Recovery path documented: `recovery.method: manual_boot_button`

**Observe integration:**
- `observe_uart` on `/dev/ttyACM0`, `baud: null`
- 4 stable expect_patterns extracted from observed boot log
- DHCP IP extraction from serial log pattern: `"IP          : (\d+\.\d+\.\d+\.\d+)"`

**Board-specific firmware extensions (new features added during migration):**
- `set_portd_output()` — drive Port D as GPIO/counter output (for loopback self-test)
- `set_sreset()` — toggle FPGA SRESET via SPI
- REST endpoints: `POST /api/portd_output`, `POST /api/reset_target`
- Web UI: Target Control panel, Port D Signal Output panel

---

### Stage E — Verify

Verification methods applied in order:

| Method | What it proves | Result |
|--------|---------------|--------|
| Serial boot log — 4 patterns | Firmware boots, FPGA configures, WiFi up, GDB ready | PASS |
| Network: ping + TCP :4242 | Device reachable, GDB service listening | PASS |
| Web API: GET /api/version | HTTPS API functional, auth working | PASS |
| Port D loopback (6 GPIO cases) | 4-bit GPIO output routed through FPGA to LA | 6/6 PASS, 100% match |
| Port D loopback (2 counter cases) | Internal counter drives LA, all 4 channels toggle | 2/2 PASS, ~50% duty |
| **Total** | | **8/8 PASS** |

The loopback self-test is closed-loop: no human inspection of waveforms needed.
AEL drives Port D → LA captures Port A → pattern validation is automatic.

---

### Stage F — Explore

Capabilities now available on this board after migration:

**Instrument use:**
- Flash and debug any DUT via SWD (GDB :4242) — already in use for STM32 boards
- Loopback-verify GPIO wiring before connecting a new DUT
- Measure DUT behavior via logic analyzer (up to 264 MHz)

**New explorable territory:**
- Port D GPIO output: can drive known patterns to DUT and confirm via LA
- SRESET: can assert/deassert target reset programmatically via AEL
- Loopback as health-check: re-run port_d_loopback.py after firmware update to confirm FPGA still healthy
- Counter mode: verifies FPGA clock and internal counter integrity
- Extended test matrix: add more GPIO patterns, ADC validation (Port A pins 0-2)

---

## Part 2 — Artifact Classification Table

### Layer 1 — Board / Project-Specific (ESP32JTAG only)

| Artifact | Path | Rationale |
|----------|------|-----------|
| Board config | `configs/boards/esp32jtag_instrument_s3.yaml` | Board-specific pins, USB serial, network |
| Instrument type | `configs/instrument_types/esp32jtag.yaml` | ESP32JTAG capability surface definition |
| Instrument instances | `configs/instrument_instances/esp32jtag_*.yaml` | Per-unit IP, serial, usage context |
| Root probe configs | `configs/esp32jtag.yaml`, `configs/esp32jtag_rp2040.yaml` | Template instances |
| Smoke test plan | `tests/plans/esp32jtag_firmware_smoke.json` | Board boot patterns, USB VID/PID |
| Loopback test plan | `tests/plans/esp32jtag_port_d_loopback.json` | P3→P0 wiring, FPGA counter modes |
| Firmware smoke pack | `packs/esp32jtag_firmware_smoke.json` | Wraps board-specific test |
| Loopback pack | `packs/esp32jtag_port_d_loopback.json` | Wraps board-specific test |
| STM32-via-JTAG packs | `packs/smoke_stm32*_esp32jtag.json` | ESP32JTAG as instrument for STM32 DUTs |
| Port D loopback script | `experiments/esp32jtag/port_d_loopback.py` | Calls FPGA-specific API, P3→P0 wiring |
| Onboarding project | `projects/esp32jtag_firmware_onboarding/` | Board-specific confirmed facts |
| Instrument interface | `ael/instruments/interfaces/esp32jtag.py` | ESP32JTAG REST API adapter |
| Flash tool script | `tools/flash_stm32_esp32jtag.sh` | ESP32JTAG GDB endpoint |
| Skills/checklists | `docs/skills/esp32jtag_*.md`, `docs/checklists/esp32jtag_*.md` | Board-specific operational knowledge |
| Design memos (2026-03-19) | `docs/` dated memos | Session artifacts — see "Not Persisted" |

**Note on `la_loopback_validation.py`:**
Currently in `ael/patterns/loopback/` (suggesting AEL-core), but:
- The binary format it decodes (`byte[0] skip + 16-bit big-endian words`) is the ESP32JTAG firmware's `/instant_capture` format
- The callables (`output_fn`, `capture_fn`) make the code generic
- In practice, no other board produces this exact binary format
**Classification:** Conditionally reusable — keep in `ael/patterns/loopback/` but document the format dependency. If a future board uses the same firmware, it works immediately. If not, the pattern serves as a template.

---

### Layer 2 — Family / Platform-Specific (ESP32 / ESP-IDF brownfield)

| Artifact | Path | Rationale |
|----------|------|-----------|
| Brownfield onboarding spec | `docs/specs/brownfield_firmware_onboarding_spec_v0_1.md` | Mostly ESP32-family, some ESP32JTAG detail mixed in |
| Migration checklist | `docs/guides/brownfield_migration_checklist.md` | ESP32 brownfield, applies to C5/C6/S3 |
| CE pattern: brownfield | EE `92fd939d` | ESP32-S3 native USB brownfield template |
| CE pattern: USB classification | EE `7daa8c80` | All ESP32 boards (dual vs native-only) |
| CE pattern: baud=null | EE `da6927bd` | All ESP32 USB CDC boards |
| Memory: USB interface rules | `memory/reference_esp32c6_dual_usb.md` | Applies to ESP32 family |

---

### Layer 3 — AEL-Core Reusable

| Artifact | Path | Rationale |
|----------|------|-----------|
| Universal bring-up spec | `docs/specs/ael_universal_bringup_spec_v1.md` | Board-agnostic method |
| PCNT loopback pattern | `ael/patterns/loopback/pcnt_loopback.py` | Firmware-only, no special hardware |
| LA loopback validation | `ael/patterns/loopback/la_loopback_validation.py` | Callable-based, format-documented |
| AEL adapters | `ael/adapters/build_idf.py`, `observe_uart_log.py` | Reusable across all ESP32/IDF boards |

---

### Not Persisted (should be archived or deleted)

| Artifact | Path | Reason |
|----------|------|--------|
| Session design memos × 8 | `docs/` files dated 2026-03-19 | Debugging session noise; superseded by project.yaml and specs |
| `onboarding_notes.md` | `projects/esp32jtag_firmware_onboarding/onboarding_notes.md` | Session notes; permanent facts already in project.yaml |

---

## Part 3 — Corrected Artifact Structure

Ground truth: what should live where, based on real outputs.

```
docs/
  specs/
    ael_universal_bringup_spec_v1.md                  [AEL-CORE] Method definition
    ael_artifact_classification_rules_v1.md            [AEL-CORE] Classification rules (NEW)
    esp32_family_brownfield_migration_guide_v1.md      [FAMILY]   ESP32 migration guide (NEW)
    brownfield_firmware_onboarding_spec_v0_1.md        [FAMILY]   Existing spec (valid, keep)
    esp32jtag_migration_method_record_v1.md            [BOARD]    This document
    archive/
      [moved here] esp32jtag_instrument_api_*.md       Session memos, no longer needed
      [moved here] esp32jtag_interface_gap_matrix_*.md
      [moved here] esp32jtag_lifecycle_boundary_*.md
      [moved here] esp32jtag_native_api_closeout_*.md
      [moved here] esp32jtag_optional_lifecycle_*.md
      [moved here] esp32jtag_probe_cfg_regression_*.md
      [moved here] shared_instrument_resource_model_*.md
  guides/
    brownfield_migration_checklist.md                  [FAMILY]   ESP32 checklist (valid, keep)
  skills/
    esp32jtag_native_api_minimal_integration.md        [BOARD]    Keep
    esp32jtag_runtime_surface_alignment.md             [BOARD]    Keep
  checklists/
    esp32jtag_acceptance_test_checklist_v0_1.md        [BOARD]    Keep

configs/
  boards/
    esp32jtag_instrument_s3.yaml                       [BOARD]
    stm32f407_discovery_esp32jtag.yaml                 [BOARD]
  instrument_types/
    esp32jtag.yaml                                     [BOARD]
  instrument_instances/
    esp32jtag_*.yaml                                   [BOARD — per unit]
  esp32jtag.yaml                                       [BOARD — template instance]
  esp32jtag_rp2040.yaml                                [BOARD]

experiments/
  esp32jtag/
    port_d_loopback.py                                 [BOARD]
    __init__.py

tests/plans/
  esp32jtag_firmware_smoke.json                        [BOARD]
  esp32jtag_port_d_loopback.json                       [BOARD]

packs/
  esp32jtag_firmware_smoke.json                        [BOARD]
  esp32jtag_port_d_loopback.json                       [BOARD]
  smoke_stm32*_esp32jtag.json                          [BOARD — ESP32JTAG as instrument]

projects/
  esp32jtag_firmware_onboarding/
    project.yaml                                       [BOARD] Keep — confirmed facts
    onboarding_notes.md                                [BOARD] Archive — session notes

ael/
  patterns/
    loopback/
      la_loopback_validation.py                        [CONDITIONALLY REUSABLE]
      pcnt_loopback.py                                 [AEL-CORE]
  instruments/
    interfaces/
      esp32jtag.py                                     [BOARD]
  adapters/
    build_idf.py                                       [FAMILY]
    observe_uart_log.py                                [FAMILY]
```

---

## Part 6 — What Should Be Moved, Renamed, Rewritten, or Removed

| Action | Item | Reason |
|--------|------|--------|
| MOVE to `docs/specs/archive/` | 8 session design memos (2026-03-19) | Superseded, no ongoing value |
| MOVE to `docs/specs/archive/` | `onboarding_notes.md` | Facts already in project.yaml |
| CREATE | `docs/specs/archive/` directory | Holds superseded session memos |
| UPDATE | `brownfield_firmware_onboarding_spec_v0_1.md` | Extract the few ESP32JTAG-specific examples into notes; section 6 should reference this board but not mix in |
| CLARIFY | `la_loopback_validation.py` docstring | Add "Binary format: ESP32JTAG /instant_capture protocol" so users know the format dependency |
| KEEP as-is | Everything else listed in Layer 1 / Layer 2 | Already in correct location |
