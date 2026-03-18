# STM32F407 Discovery Validation Session Record

**Date:** 2026-03-18
**Board:** STM32F407VGT6 — STM32F4 Discovery
**Instrument:** ST-Link V2 (onboard)
**Result:** 7/7 PASS

This document records the full details of the STM32F407 Discovery validation session,
covering: what the tests are and how they were generated, how the system is physically
set up and what instruments are used, and the division of labor between human and AI.

---

## Part 1 — The Tests: What They Are and How They Were Generated

### The Core Design: The AEL Mailbox

All tests in the AEL system are built around a single central idea: the **debug mailbox**.
This is a 16-byte struct placed at a fixed address in the MCU's SRAM:

```c
typedef struct {
    uint32_t magic;       // 0xAE100001 — marks the struct as valid
    uint32_t status;      // 0=EMPTY, 1=RUNNING, 2=PASS, 3=FAIL
    uint32_t error_code;  // test-specific failure encoding
    uint32_t detail0;     // diagnostic: byte received, count, ADC reading, etc.
} ael_mailbox_t;
```

For the STM32F407, the mailbox is placed at **`0x2001FC00`** — the top 1KB of SRAM1
(the chip has 192KB total SRAM). The firmware writes into this struct as it runs. The
host reads it back over SWD via GDB after the firmware has had time to execute. There is
no UART console, no semihosting, no special runtime communication — just a memory read
over the debug port that is already present for flashing.

This design makes the firmware fully standalone. The test result is simply sitting in RAM
waiting to be read.

### How the Firmware Was Generated

Every firmware binary for every test was written by Claude (the AI), not by a human. The
firmware is bare-metal C using direct register access — no HAL, no CMSIS library, no
vendor SDK. All register addresses, bit positions, clock divisor calculations, baud rate
math, prescaler values, and ADC configurations were derived from the STM32F4 reference
manual and written from scratch.

Each firmware follows the same structure:
1. Enable peripheral clocks via RCC registers
2. Configure GPIO pins (mode, alternate function, pull resistors)
3. Configure the peripheral under test (timer, USART, SPI, ADC, EXTI)
4. Call `ael_mailbox_init()` — writes magic and sets status = RUNNING
5. Run the experiment
6. Call `ael_mailbox_pass()` or `ael_mailbox_fail(error_code, detail)` based on outcome
7. Keep incrementing `detail0` after PASS to prove the firmware is still alive

The test plan JSON files, board config YAML files, and instrument config YAML files were
also all written by Claude.

### The 7 Tests

#### Test 1: `stm32f407_mailbox` — Basic Blink and Mailbox
**Peripheral under test:** RCC, GPIOD, basic loop timing
**What it does:** Enables GPIOD, blinks the green LED (PD12) at ~1Hz using a software
delay loop. After the first complete blink cycle (on + off), writes PASS to the mailbox.
`detail0` counts the number of completed blink cycles.
**Wiring required:** None — LED is onboard.
**Purpose:** This is the entry-level sanity check. If the chip is alive, clocks are
running, and the mailbox mechanism works, this passes. Nothing else is worth testing if
this fails.

#### Test 2: `stm32f407_timer_mailbox` — Hardware Timer Interrupt
**Peripheral under test:** TIM3, NVIC, interrupt delivery
**What it does:** Configures TIM3 with PSC=15999 and ARR=99, producing a 100ms interrupt
period at 16MHz HSI (16MHz / 16000 / 100 = 10Hz). The ISR (`TIM3_IRQHandler`) increments
a counter and updates `detail0`. After 10 interrupts (~1 second), writes PASS. The main
loop uses the `WFI` (wait-for-interrupt) instruction between ticks.
**Wiring required:** None.
**Purpose:** Proves the timer peripheral and NVIC interrupt controller both work. A chip
can have working GPIO but broken timers; this test separates them.

#### Test 3: `stm32f407_gpio_loopback` — GPIO Round-Trip
**Peripheral under test:** GPIOB input and output
**What it does:** PB0 is configured as output push-pull. PB1 is configured as input with
pull-down. The firmware drives PB0 high, waits 1ms, reads PB1 (expects 1). Drives PB0
low, reads PB1 (expects 0). Repeats 10 cycles. PASS after all 10 succeed. Error code
`0x01` = high-state read failed, `0x02` = low-state read failed.
**Wiring required:** PB0 → PB1 jumper wire.
**Purpose:** Proves GPIO output driving and input reading through an actual external
signal path. The pull-down on PB1 ensures a definite low reading when PB0 is not driven.

#### Test 4: `stm32f407_uart_loopback` — UART Self-Loopback
**Peripheral under test:** USART2, APB1 clock, GPIO alternate function
**What it does:** Configures USART2 on PD5 (TX, AF7) and PD6 (RX, AF7) at 115200 baud
8N1. BRR register value = 0x8B (computed: 16MHz / (16 × 115200) = 8.68). Sends 4 bytes
`{0x55, 0xAA, 0x12, 0x34}` one at a time. After each byte is sent, waits for RX with a
timeout (~10ms). PASS after all 4 bytes are received back and matched. Error code
`0x10|i` = RX timeout on byte i, `0x20|i` = received byte mismatch on byte i, `detail0`
= received byte value on mismatch.
**Wiring required:** PD5 → PD6 jumper wire.
**Design note:** USART1 on PA9/PA10 was deliberately avoided. On some STM32F4 Discovery
revisions, those pins are internally connected to the ST-Link UART bridge, which prevents
self-loopback. This was identified during bringup and USART2/PD5/PD6 was chosen instead.

#### Test 5: `stm32f407_exti_trigger` — External Interrupt via SYSCFG Routing
**Peripheral under test:** SYSCFG EXTI routing, EXTI edge detection, NVIC
**What it does:** PB8 is configured as output (stimulus), PB9 as input with pull-down
routed to EXTI9 via `SYSCFG_EXTICR3`. EXTI9 is configured for rising-edge trigger,
unmasked, and enabled in NVIC (IRQ 23). The firmware drives 10 rising edges from PB8
(low→high pulses, 1ms per state). Each edge fires `EXTI9_5_IRQHandler`, which increments
a counter and updates `detail0`. PASS after all 10 interrupts received. On timeout,
error code `0x01` with `detail0` = interrupts actually received.
**Wiring required:** PB8 → PB9 jumper wire.
**Purpose:** This is the most complex interrupt test. It exercises the full EXTI routing
path — GPIO → SYSCFG → EXTI → NVIC — rather than just an internal timer interrupt.

#### Test 6: `stm32f407_adc_loopback` — ADC Voltage Readback
**Peripheral under test:** ADC1, analog GPIO mode, APB2 clock
**What it does:** PC0 is a digital output (driver pin). PC1 is configured as analog input
connected to ADC1_IN11. ADC1 is configured for 12-bit single-conversion, software start,
480-cycle sample time, ADC clock = 8MHz (ADCPRE=/2 from 16MHz HSI). Drives PC0 high,
reads ADC — expects > 3000 counts (~2.4V threshold). Drives PC0 low, reads ADC — expects
< 500 counts (~0.4V threshold). Repeats 5 cycles. PASS after all 5 succeed. Error code
`0x01` = high reading too low (coupling failed), `0x02` = low reading too high.
**Wiring required:** PC0 → PC1 jumper wire.
**Purpose:** A digital GPIO driving a 12-bit ADC input proves that the analog subsystem
is functional. The thresholds are deliberately wide (3000/500 out of 4095) to tolerate
minor voltage drop across the jumper wire.

#### Test 7: `stm32f407_spi_loopback` — SPI Full-Duplex Self-Loopback
**Peripheral under test:** SPI2, APB1 clock, GPIO alternate function 5
**What it does:** SPI2 configured as master, 8-bit, mode 0 (CPOL=0 CPHA=0), BR=/256
(~62kHz at 16MHz HSI), software NSS (SSM=1 SSI=1). PB13=SCK, PB14=MISO (AF5), PB15=MOSI
(AF5). Sends 4 bytes `{0xA5, 0x5A, 0xF0, 0x0F}` one at a time. Each `spi_transfer()`
call waits for TXE, writes DR, waits for RXNE, reads DR, waits for BSY clear. PASS after
all 4 bytes echoed back and matched. Error code `0x10|i` = timeout on byte i, `0x20|i` =
mismatch on byte i, `detail0` = received byte on mismatch.
**Wiring required:** PB15 (MOSI) → PB14 (MISO) jumper wire. SCK (PB13) does not need
looping back.
**Purpose:** Full-duplex SPI in loopback mode confirms SPI master clock generation,
data shift register, and MISO/MOSI routing all function correctly.

### The Flash and Verify Process (Step by Step)

When `ael run --test <plan>` or `ael pack --pack <pack>` is executed, the pipeline runs
these stages in order:

**Stage 1 — Build**
Runs `make` in the firmware target directory. Produces an `.elf` file. Since firmware
rarely changes between runs, `make` usually completes immediately ("Nothing to be done").

**Stage 2 — Flash (resilience ladder)**
Invokes `arm-none-eabi-gdb` in batch mode, connecting to `st-util` on `127.0.0.1:4242`.
The exact GDB commands come from the board config:
```
file {firmware.elf}        ← load symbol file
load                       ← write firmware to flash over SWD
monitor reset run          ← release halt, let the MCU start executing
disconnect
```
The `monitor reset run` step is critical: `st-util` leaves the target halted after `load`
completes. Without it the MCU never starts and the mailbox remains empty. This was
discovered and fixed during bringup.

If attempt 1 fails, the pipeline retries with modified parameters (reduced SWD speed,
different reset strategy, reconnect) up to 4 attempts before declaring flash failure.

**Stage 3 — Settle**
Waits `post_load_settle_s = 2.0` seconds. This gives the firmware time to execute and
write its PASS result to the mailbox before the host attempts to read it.

**Stage 4 — Verify (mailbox read)**
Invokes `arm-none-eabi-gdb` again in batch mode:
```
target extended-remote 127.0.0.1:4242
x/4xw 0x2001FC00          ← read 4 words at mailbox address
detach
quit
```
`skip_attach=true` is set because `st-util` does not support the BMDA-style
`monitor swdp_scan` / `attach` commands used with ESP32JTAG. The Python adapter
(`check_mailbox_verify.py`) parses GDB's hex output, checks that `magic == 0xAE100001`
and `status == 2 (PASS)`, and writes a structured JSON artifact. The full result
including `error_code` and `detail0` is saved regardless of pass or fail.

**Stage 5 — Report**
Writes `result.json`, `evidence.json`, `run_plan.json`, and `runtime_state.json` to a
timestamped run directory under `runs/`. Updates the Last-Known-Good (LKG) record.

### Issues Discovered and Fixed During Bringup

**`monitor reset run` missing initially**
After `load`, the target stayed halted. GDB confirmed flash success but the MCU never
ran. Mailbox read back all zeros (no magic). Fix: add `monitor reset run` before
`disconnect` in `gdb_launch_cmds`.

**`skip_attach` required for st-util**
The standard BMDA flow uses `monitor swdp_scan` + `attach 1`. `st-util` does not support
these commands — it presents the target directly on connect. Without `skip_attach=true`,
the mailbox read step would emit "monitor command not supported" and fail to parse any
memory content.

**PA9/PA10 occupied on F4 Discovery**
The initial UART test was written for USART1 on PA9/PA10. On the Discovery board, those
pins are routed to the ST-Link UART bridge for host communication. This prevents
self-loopback because TX goes to the host PC rather than back to RX. The test was
rewritten to use USART2 on PD5/PD6, which are not connected to anything onboard.

**USB enumeration / libusb stuck state**
After a session involving a different ST-Link device, `st-info --probe` would return
"Found 0 stlink programmers" even though `lsusb` showed the device at `0483:3748`. The
libusb context inside `st-info`/`st-util` had entered a stuck state from the previous
USB activity. Fix: physical USB replug followed immediately by `st-info --probe` (before
launching `st-util`) resets the enumeration state. This ordering — probe first, then
start the GDB server — is now the established startup procedure.

**SPI MOSI→MISO jumper missing (discovered during this session)**
Tests 1–6 passed but test 7 failed with `error_code=0x20` and `detail0=0`. Error code
`0x20` means "byte 0 mismatch", and `detail0=0` means the received byte was `0x00` — SPI
is running but MISO is reading zero because the loopback wire was absent. Once PB15→PB14
was jumpered, the test passed immediately.

---

## Part 2 — System Setup and Instruments

### Two Instruments in This Lab

The lab uses two different instruments across all validated boards. Both serve the same
logical purpose — flash firmware and read back results — but through different physical
paths.

### Instrument 1: ESP32JTAG (used for most boards)

This is a custom instrument: an ESP32 microcontroller running firmware that turns it into
a wireless debug probe. It exposes two independent capability surfaces:

**Surface A — GDB Remote (SWD over bit-bang)**
The ESP32 bit-bangs the SWD protocol (SWDIO + SWDCLK) directly from its GPIO pins. It
runs a GDB remote protocol server compatible with Black Magic Probe / BMDA. The host
connects via `arm-none-eabi-gdb` over TCP/IP using `monitor swdp_scan` + `attach 1` to
reach the target.

**Surface B — Web API (GPIO/ADC control)**
The ESP32 also runs an HTTPS server exposing REST endpoints. The host can drive GPIO
outputs, read GPIO inputs, read ADC channels, and assert reset on the target. This is
used for signal observation on boards where the host needs to inject stimulus or read
signals independently of the MCU's own firmware.

**Physical wiring (for ESP32JTAG boards):**
```
Host PC ──── WiFi ────► ESP32
                           │ SWDIO  ──► DUT SWDIO
                           │ SWDCLK ──► DUT SWDCLK
                           │ GND    ──► DUT GND
                           │ P0.0   ──► DUT PA2   (observation)
                           │ P0.1   ──► DUT PA3
                           │ P0.2   ──► DUT PB13
                           │ LED    ──► DUT PC13
```

Each ESP32JTAG instance has a fixed IP address on the local network:

| Instance ID | IP Address | Used for |
|---|---|---|
| `esp32jtag_stm32f411` | 192.168.2.103 | STM32F411CEU6 Black Pill |
| `esp32jtag_g431_bench` | 192.168.2.62 | STM32G431CBU6 |
| `esp32jtag_stm32_golden` | 192.168.2.109 | STM32F401RCT6, STM32F103RCT6 (bare board) |

### Instrument 2: ST-Link V2 (used for STM32F4 Discovery)

The STM32F4 Discovery board has a built-in ST-Link V2 debug chip on the PCB itself.
This is ST's own hardware — it handles the USB-to-SWD conversion in hardware rather than
bit-bang. No external wiring to the target is needed; the SWD connection is internal
board traces.

**Physical connection:**
```
Host PC ──── USB (VID:PID 0483:3748) ──── ST-Link V2 (on Discovery PCB)
                                                  │ SWD (internal traces)
                                                  ▼
                                          STM32F407VGT6 (MCU under test)
```

**Software stack:**
```
arm-none-eabi-gdb
      │ TCP :4242 (loopback)
      ▼
  st-util (GDB server, built from source v1.8.0-99)
      │ libusb
      ▼
  ST-Link V2 USB device
      │ SWD
      ▼
  STM32F407 MCU
```

`st-util` is built from source and installed at
`instruments/STLinkInstrument/install/bin/`. It requires `LD_LIBRARY_PATH` to be set
because `libstlink.so.1` is not in the system library path. It must be started manually
before running tests — the pipeline does not auto-launch it.

### Instrument Comparison

| Attribute | ESP32JTAG | ST-Link V2 |
|---|---|---|
| Hardware origin | Custom-built ESP32 module | ST's chip on Discovery PCB |
| Host connection | WiFi (TCP) | USB (local loopback) |
| SWD method | Bit-bang from GPIO | Hardware in ST-Link chip |
| GDB server | Runs on ESP32 | `st-util` on host PC |
| GDB attach protocol | BMDA (`monitor swdp_scan` + `attach`) | Direct (no attach needed) |
| Extra capabilities | GPIO in/out, ADC, web API | SWD only |
| GDB port | 4242 | 4242 (or 4243 for F103 dongle) |
| Boards using it | F411, F401, G431, H750, F103 bare | F407 Discovery, F103 (planned) |

### Physical Bench Layout for the F407 Session

```
┌──────────────────────────────────┐
│         Host PC (Linux)          │
│  AEL Python pipeline             │
│  arm-none-eabi-gdb               │
│  st-util (port 4242)             │
└────────────────┬─────────────────┘
                 │ USB cable
                 ▼
┌──────────────────────────────────┐
│      STM32F4 Discovery Board     │
│  ┌────────────────────────────┐  │
│  │  ST-Link V2 (onboard chip) │  │
│  └───────────────┬────────────┘  │
│                  │ SWD (PCB)     │
│  ┌───────────────▼────────────┐  │
│  │     STM32F407VGT6          │  │
│  └────────────────────────────┘  │
│                                  │
│  Jumper wires (set once):        │
│    PD5  ─────── PD6              │  UART TX→RX
│    PB0  ─────── PB1              │  GPIO loopback
│    PB8  ─────── PB9              │  EXTI trigger
│    PC0  ─────── PC1              │  ADC loopback
│    PB15 ─────── PB14             │  SPI MOSI→MISO
└──────────────────────────────────┘
```

All 5 jumper wires are placed once at the start and left in place for all 7 tests. Tests
1 and 2 use no external pins; the wires are present but inactive during those tests.

### ST-Link Startup Procedure (Confirmed Working 2026-03-18)

The ST-Link USB device can enter a stuck libusb state if another ST-Link session ended
abnormally. The following procedure reliably recovers it:

1. Physically unplug the Discovery board USB cable
2. Wait 5 seconds
3. Plug back in
4. Immediately run `st-info --probe` (before starting st-util):
   ```
   INSTALL=/nvme1t/work/codex/ai-embedded-lab/instruments/STLinkInstrument/install
   LD_LIBRARY_PATH=$INSTALL/lib $INSTALL/bin/st-info --probe
   ```
   Expected: `Found 1 stlink programmers` with chipid `0x413` (STM32F4x5/F4x7)
5. Start st-util:
   ```
   LD_LIBRARY_PATH=$INSTALL/lib $INSTALL/bin/st-util 4242 &
   ```
   (Note: `--port` flag is not valid; pass the port as a positional argument)

---

## Part 3 — Division of Labor: Human vs. AI

### What the Human Was Responsible For

**Physical lab setup (one-time per board)**
- Connecting USB cables (Discovery board to host PC)
- Wiring the ESP32JTAG instrument to bare boards (SWDIO, SWDCLK, GND, 3.3V, observation
  pins) for boards without onboard debug adapters
- Placing loopback jumper wires on the target board before running the test suite

The system is explicitly designed around the constraint that wires are placed once and
never changed mid-suite. No test requires re-wiring between runs.

**Physical recovery when hardware gets stuck**
When the ST-Link USB entered the stuck libusb state, no software action could fix it.
The only resolution was physically unplugging and replugging the USB cable — a 5-second
human action. Without it the session cannot continue.

**Building and maintaining the ESP32JTAG instrument**
The ESP32JTAG is custom hardware the human designed and built. The AI writes configuration
files that reference its IP address and capability surfaces but did not create the device.

**High-level direction**
Deciding which boards to validate, which peripheral categories to cover, and what the
overall goals of the AEL system are — these decisions came from the human side. The AI
executed against those requirements.

### What the AI (Claude) Did

**All firmware, zero exceptions.**
Every `main.c` for every test on every board was written by Claude. Bare-metal C, direct
register access, no HAL, no CMSIS, no vendor SDK. All calculations (baud rates, timer
periods, ADC prescalers, GPIO alternate function assignments, NVIC IRQ numbers) were
performed from the reference manual.

**The mailbox protocol itself.**
The `ael_mailbox_t` struct, magic number (`0xAE100001`), status encoding, memory address
placement strategy, and the `ael_mailbox_init()` / `ael_mailbox_pass()` /
`ael_mailbox_fail()` inline functions were designed and implemented by Claude.

**All test plan JSON files.**
Mailbox address, settle time, wiring declarations, build paths — all authored by Claude.

**All board config YAML files.**
Instrument binding, GDB command sequences, flash parameters, post-load settle times — all
authored by Claude.

**All instrument instance config YAML files.**
IP addresses, ports, capability surface mappings — all authored by Claude.

**Pipeline code modifications.**
When new requirements emerged (e.g., `halt_before_read` for st-util, `mailbox_verify_defaults`
merging from board config), Claude modified the Python pipeline adapters accordingly.

**All diagnosis during bringup.**
- Identified that `monitor reset run` was needed after `load` (target was staying halted)
- Identified that `skip_attach=true` was needed for st-util (different GDB attach protocol)
- Identified that PA9/PA10 were occupied by the ST-Link UART bridge and switched to PD5/PD6
- Today: diagnosed the SPI failure from `error_code=0x20` + `detail0=0` → deduced the
  loopback jumper was missing without having to run any additional diagnostic step

**Running all AEL commands.**
All `ael run`, `ael pack`, `st-info --probe`, `st-util` invocations during the session
were executed by Claude.

### Summary Table

| Task | Responsible party |
|---|---|
| Write firmware (all boards, all tests) | AI |
| Design mailbox protocol | AI |
| Write test plan JSON files | AI |
| Write board config YAML files | AI |
| Write instrument instance configs | AI |
| Write / modify pipeline Python code | AI |
| Run test commands and evaluate results | AI |
| Diagnose failures from logs and error codes | AI |
| Build the ESP32JTAG instrument (hardware) | Human |
| Place loopback jumper wires on target board | Human |
| Plug in USB cables | Human |
| Physical USB replug on stuck ST-Link | Human |
| Define which boards and peripherals to test | Collaborative |
| Design AEL system architecture | Collaborative |

**The one-sentence answer:** Every line of code in this system — firmware, pipeline,
configs, test plans — was written by the AI. The only human actions required were
physical: connecting wires, plugging in hardware, and occasionally recovering a stuck
USB device by hand.

---

## Appendix: Validated Board Registry (as of 2026-03-18)

| Board | Instrument | Tests | Status |
|---|---|---|---|
| STM32F411CEU6 (Black Pill) | ESP32JTAG WiFi | 8 | Verified |
| STM32F401RCT6 | ESP32JTAG WiFi | 8 | Verified |
| STM32G431CBU6 | ESP32JTAG WiFi | 8 | Verified |
| STM32H750VBT6 | ESP32JTAG WiFi | 7 | Verified |
| STM32F103RCT6 (bare, via ESP32JTAG) | ESP32JTAG WiFi | 7 | Verified |
| STM32F407VGT6 (Discovery) | ST-Link V2 onboard | 7 | Verified 2026-03-18 |
| STM32F103RCT6 (via ST-Link dongle) | ST-Link V2 dongle | 7 | Code ready, not yet validated |
