/*
 * STM32H750VBT6 — GPIO Loopback Test
 *
 * Tests PB8 (output push-pull) → PB9 (input floating) loopback.
 * Performs 5 high/low cycles (10 reads total).
 *
 * Error bits in error_code:
 *   bit 0: ERR_HIGH — drove PB8=H, read PB9=L
 *   bit 1: ERR_LOW  — drove PB8=L, read PB9=H
 *
 * detail0 on FAIL = number of correct reads (0..10).
 * On PASS detail0 = 10, then increments each ms tick.
 *
 * All register addresses from RM0433 (STM32H750 Reference Manual).
 */

#define AEL_MAILBOX_ADDR  0x38000000u
#include "../ael_mailbox.h"

/* ---- RCC (RM0433 §8) ---------------------------------------------------- */

#define RCC_BASE            0x58024400u
#define RCC_AHB4ENR         (*(volatile uint32_t *)(RCC_BASE + 0x0E0u))
#define RCC_AHB4ENR_GPIOBEN (1u << 1)

/* ---- GPIOB (RM0433 §10, base 0x58020400) -------------------------------- */

#define GPIOB_BASE   0x58020400u
#define GPIOB_MODER  (*(volatile uint32_t *)(GPIOB_BASE + 0x00u))
#define GPIOB_IDR    (*(volatile uint32_t *)(GPIOB_BASE + 0x10u))
#define GPIOB_ODR    (*(volatile uint32_t *)(GPIOB_BASE + 0x14u))

/* ---- SysTick (ARMv7-M ARM) ---------------------------------------------- */

#define SYST_CSR        (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR        (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR        (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

/* ---- Error bits --------------------------------------------------------- */

#define ERR_HIGH  (1u << 0)
#define ERR_LOW   (1u << 1)

/* ---- Helpers ------------------------------------------------------------ */

static void delay_ticks(uint32_t ticks)
{
    for (volatile uint32_t i = 0u; i < ticks; i++) {
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

/* ---- Main --------------------------------------------------------------- */

int main(void)
{
    /* SysTick: processor clock (64 MHz HSI), RVR=63999 → 1 ms/tick */
    SYST_RVR = 63999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    /* Enable GPIOB clock */
    RCC_AHB4ENR |= RCC_AHB4ENR_GPIOBEN;
    (void)RCC_AHB4ENR;

    ael_mailbox_init();

    /* PB8: output push-pull (MODER bits [17:16] = 01) */
    GPIOB_MODER &= ~(0x3u << 16u);
    GPIOB_MODER |=  (0x1u << 16u);

    /* PB9: input floating (MODER bits [19:18] = 00) */
    GPIOB_MODER &= ~(0x3u << 18u);

    uint32_t err         = 0u;
    uint32_t correct     = 0u;

    /* 5 high/low cycles = 10 reads */
    for (uint32_t cycle = 0u; cycle < 5u; cycle++) {
        /* Drive high, settle 2 ms, read PB9 */
        GPIOB_ODR |= (1u << 8u);
        delay_ticks(2u);
        if ((GPIOB_IDR & (1u << 9u)) != 0u) {
            correct++;
        } else {
            err |= ERR_HIGH;
        }

        /* Drive low, settle 2 ms, read PB9 */
        GPIOB_ODR &= ~(1u << 8u);
        delay_ticks(2u);
        if ((GPIOB_IDR & (1u << 9u)) == 0u) {
            correct++;
        } else {
            err |= ERR_LOW;
        }
    }

    if (err == 0u) {
        ael_mailbox_pass();
        /* PASS: detail0 starts at 10 (all correct), increments each ms */
        uint32_t iteration = correct;   /* == 10 */
        while (1) {
            delay_ticks(1u);
            iteration++;
            AEL_MAILBOX->detail0 = iteration;
        }
    } else {
        ael_mailbox_fail(err, correct);
        while (1) {}
    }
}
