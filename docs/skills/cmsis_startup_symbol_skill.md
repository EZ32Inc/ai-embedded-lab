# CMSIS Startup Symbol Skill

## Purpose

Prevent linker errors caused by missing symbols when porting bare-metal
firmware to a new STM32 (or other ARM Cortex-M) target.

Based on real incident: STM32F401RCT6 bringup (2026-03-15), all 7 banner
firmwares failed with `undefined reference to '_sidata'` until the linker
script was corrected.

---

## Trigger

Use this skill whenever:

- Creating a new firmware target for a new MCU
- Porting a linker script from one STM32 variant to another
- Encountering `undefined reference` errors from a startup `.s` file
- Switching CMSIS startup file versions (e.g. `startup_stm32f411xe.s` → `startup_stm32f401xc.s`)

---

## Core Rule

Different CMSIS startup file versions reference different external symbols.
**Never assume the linker script from one MCU variant works for another.**

Before compiling, verify that every external symbol referenced in the
startup `.s` file is defined in the linker script.

---

## How to Check

### Step 1: Find all external symbol references in the startup file

```bash
grep -E "^\s+(ldr|b|bl)\s+.*=\s*_|EXTERN|__" startup_stm32f4*.s \
  | grep -v "//" | sort -u
```

Common symbols to look for:

| Symbol | Meaning | Linker script definition |
|--------|---------|--------------------------|
| `_sidata` | Flash load address of .data section | `_sidata = LOADADDR(.data);` |
| `_sdata` | Start of .data in RAM | `_sdata = .;` inside `.data` |
| `_edata` | End of .data in RAM | `_edata = .;` inside `.data` |
| `_sbss` | Start of .bss | `_sbss = .;` inside `.bss` |
| `_ebss` | End of .bss | `_ebss = .;` inside `.bss` |
| `_estack` | Top of stack | `_estack = ORIGIN(RAM) + LENGTH(RAM);` |

### Step 2: Verify each symbol is defined in the linker script

```bash
grep "_sidata\|_sdata\|_edata\|_sbss\|_ebss\|_estack" your_linker.ld
```

Every symbol found in Step 1 must appear in this output.

### Step 3: Fix missing symbols

The most commonly missing symbol when porting from F411 → F401:

```ld
/* Add inside the .data section, before _sdata: */
.data :
{
    _sidata = LOADADDR(.data);   /* ← this line */
    _sdata = .;
    *(.data*)
    _edata = .;
} > RAM AT > FLASH
```

---

## Why This Happens

CMSIS startup files evolved across STM32 product lines.
Older variants (e.g. F411) use `AT` syntax in the linker script directly
and do not need `_sidata`. Newer variants (e.g. F401xC) require the
startup file to receive `_sidata` as an explicit symbol.

When porting a linker script between variants, this mismatch is silent
until link time.

---

## Checklist

- [ ] Identified startup file version for the new target
- [ ] Grepped startup file for all external symbol references
- [ ] Confirmed every referenced symbol is defined in the linker script
- [ ] Test-compiled before adding firmware logic (catch linker errors early)
