#include <stdint.h>

/*
 * STM32H750VBT6 minimal startup
 *
 * Reset_Handler structure reused from G431 pattern.
 * Vector table size and memory symbols are H750-specific (RM0433).
 *
 * Cortex-M7 core exceptions: 16 entries (indices 0-15).
 * Peripheral IRQs: not needed for minimal firmware — omitted.
 * The vector table only needs to cover what minimal firmware uses.
 */

extern int main(void);

extern uint32_t _estack;
extern uint32_t _etext;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

void Reset_Handler(void);
void Default_Handler(void);

__attribute__((section(".isr_vector")))
void (*const vector_table[])(void) = {
    (void (*)(void))(&_estack),   /* 0x00: Initial stack pointer */
    Reset_Handler,                 /* 0x04: Reset */
    Default_Handler,               /* 0x08: NMI */
    Default_Handler,               /* 0x0C: HardFault */
    Default_Handler,               /* 0x10: MemManage */
    Default_Handler,               /* 0x14: BusFault */
    Default_Handler,               /* 0x18: UsageFault */
    0,                             /* 0x1C: Reserved */
    0,                             /* 0x20: Reserved */
    0,                             /* 0x24: Reserved */
    0,                             /* 0x28: Reserved */
    Default_Handler,               /* 0x2C: SVCall */
    Default_Handler,               /* 0x30: DebugMon */
    0,                             /* 0x34: Reserved */
    Default_Handler,               /* 0x38: PendSV */
    Default_Handler,               /* 0x3C: SysTick */
};

void Reset_Handler(void)
{
    /* Copy .data section from flash to DTCM */
    uint32_t *src = &_etext;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) {
        *dst++ = *src++;
    }

    /* Zero .bss section in DTCM */
    dst = &_sbss;
    while (dst < &_ebss) {
        *dst++ = 0u;
    }

    (void)main();
    while (1) {}
}

void Default_Handler(void)
{
    while (1) {}
}
