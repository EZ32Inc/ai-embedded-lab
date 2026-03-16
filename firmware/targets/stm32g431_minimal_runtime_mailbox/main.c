#include <stdint.h>
#include "../ael_mailbox.h"

/*
 * STM32G431CBU6 — Minimal Runtime Mailbox Baseline
 *
 * This is the operationally first program in any new-board bring-up sequence.
 * It proves exactly four things:
 *   1. Firmware was flashed successfully (MCU executes code)
 *   2. MCU boots from flash and reaches main()
 *   3. RAM at AEL_MAILBOX_ADDR (0x20007F00) is writable by firmware
 *   4. The SWD debug read path works (read_mailbox.py returns STATUS_PASS)
 *
 * No peripheral clocks, no GPIO loopback, no external instruments required.
 * Dependencies: SWDIO, SWCLK, GND, flash access only.
 *
 * Pass criteria (via read_mailbox.py):
 *   magic      = 0xAE100001
 *   status     = 2  (STATUS_PASS)
 *   error_code = 0
 *   detail0    increments between consecutive reads (MCU actively running)
 *
 * PA8 LED:
 *   Steady on  = PASS
 *   Rapid blink = FAIL
 */

/* ---- GPIO (PA8 LED) ----------------------------------------------------- */

#define RCC_BASE     0x40021000u
#define RCC_AHB2ENR  (*(volatile uint32_t *)(RCC_BASE + 0x4Cu))
#define GPIOA_BASE   0x48000000u
#define GPIOA_MODER  (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_ODR    (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))

/* ---- SysTick ------------------------------------------------------------ */

#define SYST_CSR  (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR  (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR  (*(volatile uint32_t *)0xE000E018u)

static void delay_ticks(uint32_t ticks)
{
    for (volatile uint32_t i = 0u; i < ticks; i++) {
        while ((SYST_CSR & (1u << 16)) == 0u) {}
    }
}

/* ---- Self-check --------------------------------------------------------- */

/*
 * Minimal self-check: basic arithmetic and a stack round-trip.
 * Deliberately trivial — if this fails the MCU has a fundamental problem.
 * Returns 0 = pass, non-zero error code = fail.
 */
static uint32_t self_check(void)
{
    volatile uint32_t a = 1u;
    volatile uint32_t b = 1u;
    if (a + b != 2u) { return 0x0001u; }   /* basic arithmetic */
    if (a * b != 1u) { return 0x0002u; }
    if (a - b != 0u) { return 0x0003u; }

    /* Constant check — verifies .text is readable */
    static const uint32_t sentinel = 0xAE100001u;
    if (sentinel != 0xAE100001u) { return 0x0004u; }

    return 0u;
}

/* ---- Main --------------------------------------------------------------- */

int main(void)
{
    /* Enable GPIOA clock; PA8 = output push-pull (status LED) */
    RCC_AHB2ENR |= (1u << 0);
    (void)RCC_AHB2ENR;
    GPIOA_MODER &= ~(0x3u << 16);
    GPIOA_MODER |=  (0x1u << 16);
    GPIOA_ODR   &= ~(1u << 8);

    /* SysTick at ~500 Hz (effective rate on this unit: ~8 MHz / 16000) */
    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = (1u << 2) | (1u << 0);

    /* Write magic + STATUS_RUNNING into mailbox.
     * Status is always written last — a partial write cannot be misread
     * as a complete result. */
    ael_mailbox_init();

    /* Run minimal self-check */
    uint32_t err = self_check();

    if (err == 0u) {
        /* --- PASS path ---
         * Write STATUS_PASS, then stay alive incrementing detail0.
         * Repeated reads will see detail0 grow, proving the MCU is
         * actively running (not stuck after a one-time write). */
        ael_mailbox_pass();
        GPIOA_ODR |= (1u << 8);   /* steady LED = PASS */

        uint32_t iteration = 0u;
        while (1) {
            delay_ticks(1u);
            iteration += 1u;
            AEL_MAILBOX->detail0 = iteration;
        }
    } else {
        /* --- FAIL path ---
         * Write error_code + STATUS_FAIL, then spin.
         * detail0 is NOT updated — a frozen detail0 on repeated reads
         * confirms the MCU halted here. */
        ael_mailbox_fail(err, 0u);

        /* Rapid blink: visual indicator of failure */
        while (1) {
            GPIOA_ODR ^= (1u << 8);
            delay_ticks(50u);   /* ~100ms per half-period */
        }
    }
}
