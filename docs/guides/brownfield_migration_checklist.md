# AEL Brownfield Migration Checklist
# Bringing a mature ESP32 project into AEL build→flash→observe→validate pipeline

This checklist is grounded in the ESP32JTAG Firmware onboarding (2026-03-24),
the first real brownfield case. Every item corresponds to a real blocker from that session.

Expected time if checklist followed from the start: ~60 minutes.
Time without checklist (as experienced): ~4 hours.

---

## Phase 0 — Project Scan (10 min)

Goal: understand the project before touching AEL config.

### Build system
- [ ] Confirm build system: ESP-IDF / CMake / Make / other
- [ ] Check if `idf.py` is in PATH: `which idf.py`
  - If not → record `idf_path` (e.g. `/home/user/esp/esp-idf`)
  - Will be needed in `board.build.idf_path`
- [ ] Check IDF version: `idf.py --version` (must be ≥5.0 for AEL adapters)

### sdkconfig state
- [ ] Does a `sdkconfig` file exist in the project?
- [ ] Is it committed to git? (`git log -- sdkconfig`)
  - If yes and tuned → **set `skip_set_target: true`** (protects from fullclean)
  - If no → AEL can regenerate it; `skip_set_target: false`
- [ ] Verify sdkconfig flash size matches hardware: `grep FLASHSIZE sdkconfig`
  - Mismatch here causes partition table check failure at build time

### Artifact layout
- [ ] Where does the project build? (project-local `build/` vs AEL `artifacts/`)
  - External projects: set `build_dir` to absolute path inside the project
- [ ] What is the main `.elf` / `.bin` name? (`ls build/*.elf build/*.bin`)
  - AEL fallback searches `build/*.elf`; explicit `artifact_stem` avoids ambiguity

---

## Phase 1 — Hardware Modeling (10 min)

Goal: fill in board YAML accurately. Wrong values here cause silent failures.

### USB interface type (most critical decision)

Ask: **does the board have a USB-to-UART bridge chip?**

| Evidence | Classification | Template to use |
|----------|---------------|----------------|
| Two USB ports, or one labeled "UART" + one "USB" | `dual` | `board_brownfield_esp32_dual_usb.yaml` |
| Single USB-C/micro connector → directly to ESP32 GPIO19/20 | `native_only` | `board_brownfield_esp32_native_usb.yaml` |
| Only a UART header, no USB at all | `bridge_only` | (manual serial adapter) |

Consequences of getting this wrong:
- `native_only` classified as `dual` → AEL attempts RTS/DTR reset → unreliable behavior
- `dual` classified as `native_only` → AEL skips available RTS/DTR → slower recovery

Confirm:
- [ ] `usb_interface_type` set in board YAML
- [ ] `console.rts_dtr_reset` set correctly (`false` for native-only)
- [ ] `console.type` set (`usb_serial_jtag` for native-only, `uart` for bridge)

### Console
- [ ] What is the `/dev/tty*` device? (`ls /dev/ttyACM* /dev/ttyUSB*` after plugging in)
- [ ] Confirm VID/PID: `udevadm info /dev/ttyACM0 | grep -E 'ID_VENDOR_ID|ID_MODEL_ID|ID_SERIAL'`
  - Espressif native USB: VID=303a PID=1001
  - CH341 bridge: VID=1a86
- [ ] Record USB serial for stable port assignment (avoids /dev/ttyACM0 vs ACM1 race)
- [ ] For native USB: `console.baud: null` (USB CDC ignores baud; AEL defaults to 115200 internally)
- [ ] For bridge: record actual baud (typically 115200)
- [ ] Does the console disappear on firmware crash? → `console.loss_on_crash: true` for native USB

### Flash
- [ ] What flash method does the project use?
  - Single binary (`idf.py flash`) → `use_flash_args: false`
  - Multi-binary with `flash_args` → `use_flash_args: true`
  - Check: `cat build/flash_args` (exists → multi-binary)
- [ ] Normal flash requires running firmware? → `requires_running_firmware: true`
- [ ] Recovery path if firmware dead: BOOT+RESET → `recovery.method: manual_boot_button`

### Network (if applicable)
- [ ] Does the firmware expose a network port? (GDB, HTTP, etc.)
- [ ] What port numbers? Record in `board.network`
- [ ] Is IP static or DHCP? Record observed DHCP IP for reference (not for hard-coding)

---

## Phase 2 — First Manual Observation (10 min)

Goal: capture boot log and extract stable `expect_patterns` before writing test plan.
**Do not skip this phase.** Guessed patterns cause silent test failures.

### Capture boot log
```bash
# Method 1: idf.py monitor (recommended, handles USB JTAG)
idf.py -p /dev/ttyACM0 -C /path/to/project monitor

# Method 2: pyserial (for scripted capture)
python3 -c "
import serial, time
s = serial.Serial('/dev/ttyACM0', 115200, timeout=0.1)
start = time.time()
while time.time() - start < 10:
    d = s.read(4096)
    if d: print(d.decode('utf-8', errors='replace'), end='')
"
```

If the device is already running, just connect — you'll see the heartbeat.
To see the full boot sequence: press RESET while the capture is running.

### Extract expect_patterns (see `observe_uart_boot_pattern_guide.md` for full rules)

Good patterns — stable across all runs:
- [ ] A "subsystem init done" line (e.g. `FPGA configured OK`)
- [ ] A "ready/listening" line (e.g. `Listening on TCP port: 4242`)
- [ ] The final boot-complete line (e.g. `[APP] Free memory:`)
- [ ] One network-up line (e.g. `GOT ip event!!!` or IP assignment)

Bad patterns — avoid:
- Lines containing memory addresses (`0x3ff...`)
- Lines containing version strings that change per build
- Lines containing timestamps in milliseconds (exact value varies)
- Lines that only appear sometimes (conditional init)

- [ ] At least 3 stable expect_patterns identified
- [ ] At least 1 pattern marks "firmware fully ready"
- [ ] Heartbeat signal identified (for ongoing-health checks)
- [ ] Note boot duration (e.g. ~4.4s for ESP32JTAG S3) for `duration_s` sizing

---

## Phase 3 — AEL Integration (15 min)

### Board YAML
- [ ] Copy appropriate template (`board_brownfield_esp32_native_usb.yaml` or `_dual_usb.yaml`)
- [ ] Fill in: name, target, project_dir, build_dir, idf_path (if needed)
- [ ] Fill in: port, usb_serial, baud
- [ ] Fill in: usb_interface_type, console.type, rts_dtr_reset
- [ ] Save to `configs/boards/<board_id>.yaml`
- [ ] Quick sanity: `python3 -c "import yaml; yaml.safe_load(open('configs/boards/<board_id>.yaml'))"`

### Test plan JSON
- [ ] Copy template (`test_plan_instrument_firmware_smoke.json`)
- [ ] Fill in: board, usb_serial, expect_patterns
- [ ] Set `duration_s` to (boot_time_s + 5s) minimum; 15s is safe default
- [ ] If network validation needed: set `validate_network` section
- [ ] Save to `tests/plans/<board_id>_smoke.json`

### Pack JSON
- [ ] Copy template (`pack_smoke.json`)
- [ ] Fill in: name, board, test plan path
- [ ] Save to `packs/<board_id>_smoke.json`

### First AEL run
```bash
cd /nvme1t/work/codex/ai-embedded-lab
python3 -m ael pack --pack packs/<board_id>_smoke.json
```

Expected output on first success:
```
Build: OK -> .../<board_id>.elf
Flash: ESP-IDF via idf.py port=...
PASS: Run verified
key_checks_passed=uart.verify
```

---

## Phase 4 — Troubleshooting (only if Phase 3 fails)

Work top-down — each stage failure blocks the next.

### Build fails
```
Build: FAIL
```
- `idf.py not found` → add `idf_path` to board config
- `set-target` errors / sdkconfig destroyed → add `skip_set_target: true`
- Flash size mismatch → `git restore sdkconfig` in project, verify `CONFIG_ESPTOOLPY_FLASHSIZE_*`
- Missing component → normal IDF dependency issue, fix in project

### Flash fails
```
Flash: no serial port found
Flash: FAIL
```
- Port not found → check `ls /dev/ttyACM*`, verify board is plugged in and firmware running
- Permission denied → `sudo usermod -a -G dialout $USER` + re-login
- Wrong port/serial → re-run `udevadm info` to confirm

### observe_uart fails — bytes_read=0
```
FAIL: stage=observe_uart
Hint: target appears stuck in ROM downloader
```
- **First check**: is `baud` set to null? (Should be fine — AEL uses 115200 default since fix)
- Port not found → device not running; check flash completed successfully
- Boot window missed → `duration_s` too short; increase by 10s
- Device actually in ROM download mode → press RESET (without holding BOOT)

### observe_uart fails — patterns missing
```
FAIL: stage=observe_uart
uart: expected UART patterns missing
```
- Pattern mismatch → re-check against actual boot log (run idf.py monitor manually)
- Pattern contains regex special chars → escape them (`(`, `)`, `[`, `]`, `.`, `*`)
- Boot takes longer than `duration_s` → increase `duration_s`
- Pattern only appears at specific boot conditions → replace with unconditional pattern

### observe_uart fails — crash detected
```
FAIL: stage=observe_uart
uart: crash detected
```
- Check if `error_patterns` matched legitimately → inspect `observe_uart.log` in run dir
- Some ESP-IDF log lines contain "failed" in INFO messages → add to `forbid_patterns` carefully

---

## Phase 5 — CE Recording (5 min)

After first successful run:

```python
import sys
sys.path.insert(0, '/nvme1t/work/codex/experience_engine')
from api import ExperienceAPI
from ael.civilization import run_index

api = ExperienceAPI()

# Record project-specific facts (scope=task or board_family)
e = api.add(
    raw='<board_id>: brownfield onboarding complete. '
        'Project: <project_path>. '
        'Key facts: <usb_interface_type>, <console_type>, <boot_patterns>. '
        'Recovery: <recovery_method>.',
    domain='engineering',
    outcome='success',
    scope='board_family',
)

run_index.record_success('<board_id>', '<test_name>', e.id)
print(f"Recorded: {e.id}")
```

If any novel pattern was discovered (new bug, new workaround, new constraint):
- Promote to `scope='pattern'` and add `[HIGH_PRIORITY]` prefix
- Add to CLAUDE.md high-priority assets table

---

## Quick Reference: Board YAML Required Fields

| Field | Native-USB-only | Dual (bridge+native) | Notes |
|-------|----------------|---------------------|-------|
| `usb_interface_type` | `native_only` | `dual` | Required |
| `console.type` | `usb_serial_jtag` | `uart` | Drives AEL behavior |
| `console.baud` | `null` | `115200` | null safe since 2026-03-24 fix |
| `console.rts_dtr_reset` | `false` | `true` | Drives reset_strategy |
| `console.loss_on_crash` | `true` | `false` | For recovery guidance |
| `flash.auto_reset` | `false` | `true` | |
| `flash.requires_running_firmware` | `true` | `true` (usually) | |
| `build.skip_set_target` | `true` (if tuned sdkconfig) | same | |
| `build.idf_path` | set if idf.py not in PATH | same | |

---

*First version derived from ESP32JTAG Firmware Brownfield Onboarding, 2026-03-24.*
*CE: pattern `92fd939d` (brownfield pattern), `7daa8c80` (USB classification).*
