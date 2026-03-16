# Spec: AEL Debug Mailbox Contract v0.1

## Status
Adopted — validated on STM32G431CBU6 (2026-03-16). First implementation confirmed on hardware.

---

## Purpose

Define the minimum shared contract that any AEL mailbox implementation must follow, so that:
- firmware on any board can write a compatible mailbox
- `read_mailbox.py` and `check.mailbox_verify` can read it without board-specific changes
- run artifacts from any board are in the same format

This is the minimum contract. Future fields may be added; existing fields must not change meaning.

---

## Memory Layout

The mailbox is a 16-byte struct at a fixed address in SRAM.

```c
typedef struct {
    uint32_t magic;       /* offset +0 */
    uint32_t status;      /* offset +4  — always written last */
    uint32_t error_code;  /* offset +8 */
    uint32_t detail0;     /* offset +12 */
} ael_mailbox_t;
```

**Address strategy:** place the mailbox at the top of SRAM, minus a 256-byte safety gap from the stack.

| Board | SRAM range | Stack top | Mailbox address |
|---|---|---|---|
| STM32G431CBU6 | 0x20000000–0x20007FFF (32 KB) | 0x20008000 | `0x20007F00` |

For new boards: choose `sram_end - 0x100` (256 bytes below stack top). Verify with `arm-none-eabi-nm` that firmware `.bss` does not reach the mailbox address.

---

## Magic Value

```c
#define AEL_MAILBOX_MAGIC  0xAE100001u
```

`magic` must be written before `status`. A reader that finds `magic != AEL_MAILBOX_MAGIC` must treat the mailbox as not yet written (MCU did not reach `main()`, or wrong address).

---

## Status Values

```c
#define AEL_STATUS_EMPTY    0u   /* mailbox not yet initialized */
#define AEL_STATUS_RUNNING  1u   /* firmware is executing, result not yet final */
#define AEL_STATUS_PASS     2u   /* test passed */
#define AEL_STATUS_FAIL     3u   /* test failed; see error_code */
```

**Status must always be written last.** The correct write sequence is:

```c
/* init */
mailbox->magic      = AEL_MAILBOX_MAGIC;
mailbox->error_code = 0;
mailbox->detail0    = 0;
mailbox->status     = AEL_STATUS_RUNNING;   /* last */

/* on pass */
mailbox->status = AEL_STATUS_PASS;          /* last */

/* on fail */
mailbox->error_code = error_code;
mailbox->detail0    = detail;
mailbox->status     = AEL_STATUS_FAIL;      /* last */
```

A partial write cannot be misread as a complete result because status is the gate field.

---

## error_code

- `0x00000000` = no error
- Non-zero = test-specific error; defined per firmware target
- Convention: upper byte = category, lower bytes = detail

Example conventions used in G431 firmware:
- `0xE001` = peripheral check failed (generic)
- `0x0001`–`0x0004` = self-check arithmetic/constant failures (minimal_runtime_mailbox)
- `0xDEAD0001` = intentional FAIL injection (PoC test only)

---

## detail0

Optional diagnostic field. Usage depends on the firmware:

- `minimal_runtime_mailbox`: loop iteration counter — increments continuously on PASS path, proving active execution
- `stm32g431_adc`: raw ADC sample value on FAIL, for range diagnosis
- All others: `0` by default unless a specific diagnostic is useful

For `minimal_runtime_mailbox` specifically: two consecutive reads of `detail0` must show an increasing value to confirm the MCU is actively running (not stuck after a one-time write).

---

## Write Rules

1. **Status written last.** Always.
2. **Magic written first.** Reader uses magic as the validity gate.
3. **No intermediate partial states.** Do not write `status = RUNNING`, then overwrite `magic`.
4. **Do not update `detail0` on the FAIL path** (unless intentional for diagnostics). A frozen `detail0` between two reads is a diagnostic signal that the MCU halted.

---

## Shared Header

All AEL firmware should use the shared header:

```c
#include "../ael_mailbox.h"   /* firmware/targets/ael_mailbox.h */
```

This header defines the struct, magic, status constants, `AEL_MAILBOX_ADDR`, and the three inline helpers: `ael_mailbox_init()`, `ael_mailbox_pass()`, `ael_mailbox_fail()`.

Do not redefine these in per-firmware files.

---

## Host Read Interface

### Command-line tool

```bash
python3 tools/read_mailbox.py --ip 192.168.2.62 [--port 4242] [--addr 0x20007F00]
```

Exit code 0 = PASS, 1 = FAIL/ERROR.

### AEL pipeline stage

Add to test plan JSON:
```json
"mailbox_verify": {
  "settle_s": 3.0,
  "addr": "0x20007F00"
}
```

This adds a `check.mailbox_verify` step after flash. The step reads the mailbox via GDB batch after `settle_s` seconds and writes `artifacts/mailbox_verify.json`.

---

## Artifact Format

`mailbox_verify.json` written by `check.mailbox_verify`:

```json
{
  "ok": true,
  "addr": "0x20007F00",
  "endpoint": "192.168.2.62:4242",
  "magic": "0xae100001",
  "magic_ok": true,
  "status": 2,
  "status_name": "PASS",
  "error_code": "0x00000000",
  "detail0": 847
}
```

On read failure:
```json
{
  "ok": false,
  "addr": "0x20007F00",
  "endpoint": "192.168.2.62:4242",
  "error": "parse_failed",
  "gdb_stdout": "...",
  "gdb_stderr": "..."
}
```

---

## Portability Checklist for New Boards

Before using the mailbox on a new board:

- [ ] Confirm SRAM address range from datasheet
- [ ] Choose mailbox address: `sram_end - 0x100`
- [ ] Verify with `arm-none-eabi-nm` that `.bss` does not overlap the mailbox address
- [ ] Update `AEL_MAILBOX_ADDR` in shared header (or override in firmware if needed)
- [ ] Verify `arm-none-eabi-gdb` can attach via `target extended-remote ip:port`
- [ ] Run `read_mailbox.py` manually to confirm before enabling `check.mailbox_verify` in pipeline

---

## Porting Note

`ael_mailbox.h` currently hardcodes `AEL_MAILBOX_ADDR = 0x20007F00` for STM32G431CBU6. When porting to a new board with a different SRAM layout, either:

1. Pass `-DAEL_MAILBOX_ADDR=0x2XXXXXXX` to the compiler, or
2. Update the header and note the board-specific value

The contract fields (magic, status encoding, write order) must not change between boards.
