#include <stdint.h>

/*
 * Override mailbox address BEFORE including the shared header.
 * H750: SRAM4 at 0x38000000 (D3 domain, AHB-accessible by CPU and debugger).
 * NOT DTCM (0x20000000) — DTCM is M7-only and NOT readable by GDB via AHB.
 * Provisional — confirmed safe via nm check (_ebss = 0x20000000, no overlap).
 */
#define AEL_MAILBOX_ADDR  0x38000000u
#include "../ael_mailbox.h"

/*
 * STM32H750VBT6 — Minimal Runtime Mailbox Baseline
 *
 * Step 0 boot gate. Proves: flash OK, MCU boots, SRAM4 writable, SWD readable.
 * No peripheral init. No cache. No PLL. No MPU. No FPU.
 *
 * All register addresses from RM0433 (STM32H750 Reference Manual).
 * Nothing inherited from G431 or F411 implementations.
 *
 * Mailbox address: 0x38000000 (SRAM4 start — PROVISIONAL)
 *   SRAM4 is in D3 domain, AHB4-accessible by CPU and debugger.
 *   NOT in DTCM (which is M7-only and debugger-inaccessible).
 *   Address confirmed safe after arm-none-eabi-nm .bss check.
 *
 * Clock: 64 MHz HSI default (no PLL configured — Step 0 rule).
 * SysTick: CLKSOURCE=1 (processor clock), RVR=63999 → 1000 Hz (1 ms/tick).
 *
 * PA8 output: status LED (active-high). Board LED may be on a different pin
 * (e.g. PE3 on YD board) — verify physically. Mailbox result does not
 * depend on LED; it is read via SWD only.
 */

/* ---- RCC (RM0433 §8) ---------------------------------------------------- */

#define RCC_BASE        0x58024400u
#define RCC_AHB4ENR     (*(volatile uint32_t *)(RCC_BASE + 0x0E0u))
#define RCC_AHB4ENR_GPIOAEN  (1u << 0)

/* ---- GPIOA (RM0433 §10, Table 5: GPIOA base 0x58020000) ----------------- */

#define GPIOA_BASE      0x58020000u
#define GPIOA_MODER     (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_ODR       (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))

/* ---- SysTick (ARMv7-M Architecture Reference Manual) -------------------- */

#define SYST_CSR        (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR        (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR        (*(volatile uint32_t *)0xE000E018u)

#define SYST_CSR_ENABLE     (1u << 0)
#define SYST_CSR_CLKSOURCE  (1u << 2)   /* 1 = processor clock */
#define SYST_CSR_COUNTFLAG  (1u << 16)

/* ---- Delay -------------------------------------------------------------- */

static void delay_ticks(uint32_t ticks)
{
    for (volatile uint32_t i = 0u; i < ticks; i++) {
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

/* ---- Self-check --------------------------------------------------------- */

static uint32_t self_check(void)
{
    volatile uint32_t a = 1u;
    volatile uint32_t b = 1u;
    if (a + b != 2u) { return 0x0001u; }
    if (a * b != 1u) { return 0x0002u; }
    if (a - b != 0u) { return 0x0003u; }

    /* .text readable: verify a constant value */
    static const uint32_t sentinel = 0xAE100001u;
    if (sentinel != 0xAE100001u) { return 0x0004u; }

    return 0u;
}

/* ---- Main --------------------------------------------------------------- */

int main(void)
{
    /*
     * Step 0 rule: do NOT enable D-cache, I-cache, PLL, MPU, or FPU.
     * Caches are off by default after reset (SCB->CCR bits not set).
     * Clock is 64 MHz HSI by default — no RCC configuration needed.
     */

    /* Enable GPIOA clock (RCC_AHB4ENR, RM0433 §8.7.37) */
    RCC_AHB4ENR |= RCC_AHB4ENR_GPIOAEN;
    (void)RCC_AHB4ENR;   /* read-back to ensure peripheral clock is active */

    /* PA8 output push-pull (LED, visual indicator only) */
    GPIOA_MODER &= ~(0x3u << 16u);
    GPIOA_MODER |=  (0x1u << 16u);
    GPIOA_ODR   &= ~(1u << 8u);

    /*
     * SysTick: processor clock (64 MHz HSI), RVR=63999 → 1000 Hz (1 ms/tick)
     * Different from G431's ~500 Hz — H750 default clock is 64 MHz, not 8 MHz.
     */
    SYST_RVR = 63999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    /*
     * Write magic + STATUS_RUNNING into mailbox at SRAM4 (0x38000000).
     * Status written last — a partial write cannot be misread as complete.
     */
    ael_mailbox_init();

    /* Run minimal self-check */
    uint32_t err = self_check();

    if (err == 0u) {
        /*
         * PASS path: write STATUS_PASS, then loop incrementing detail0.
         * Two consecutive reads of detail0 will show increasing values,
         * proving the MCU is actively running (not stuck after one write).
         */
        ael_mailbox_pass();
        GPIOA_ODR |= (1u << 8u);   /* steady on = PASS */

        uint32_t iteration = 0u;
        while (1) {
            delay_ticks(1u);
            iteration += 1u;
            AEL_MAILBOX->detail0 = iteration;
        }
    } else {
        /*
         * FAIL path: write error_code + STATUS_FAIL, then rapid blink.
         * detail0 is NOT updated — frozen detail0 on repeated reads confirms
         * the MCU halted here.
         */
        ael_mailbox_fail(err, 0u);

        while (1) {
            GPIOA_ODR ^= (1u << 8u);
            delay_ticks(100u);   /* ~100 ms per half-period at 1000 Hz */
        }
    }
}
