/*
 * STM32H750VBT6 linker script — minimal runtime mailbox
 *
 * Memory map (RM0433):
 *   FLASH  : 0x08000000  128 KB
 *   DTCM   : 0x20000000  128 KB  (M7 tightly coupled, NOT AHB-accessible)
 *   AXI RAM: 0x24000000  512 KB  (D1 domain, AHB-accessible)
 *   SRAM1  : 0x30000000  128 KB  (D2 domain, AHB-accessible)
 *   SRAM4  : 0x38000000   64 KB  (D3 domain, AHB-accessible)
 *
 * Layout chosen for minimal firmware:
 *   Stack  : DTCM top (0x20020000) — fastest RAM for M7 core
 *   .data  : DTCM, loaded from FLASH
 *   .bss   : DTCM
 *   Mailbox: SRAM4 (0x38000000) — AHB-accessible, separate from stack/bss,
 *            not in linker script (firmware writes directly via pointer)
 *
 * NOTE: DTCM is NOT accessible by the AHB bus (debugger cannot read it).
 * The mailbox must NOT be placed in DTCM. It lives at 0x38000000 (SRAM4).
 */

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 128K
    DTCM  (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
}

_estack = ORIGIN(DTCM) + LENGTH(DTCM);   /* 0x20020000 */

SECTIONS
{
    .isr_vector :
    {
        KEEP(*(.isr_vector))
    } > FLASH

    .text :
    {
        *(.text*)
        *(.rodata*)
    } > FLASH

    _etext = .;

    .data :
    {
        _sdata = .;
        *(.data*)
        _edata = .;
    } > DTCM AT > FLASH

    .bss :
    {
        _sbss = .;
        *(.bss*)
        *(COMMON)
        _ebss = .;
    } > DTCM
}
