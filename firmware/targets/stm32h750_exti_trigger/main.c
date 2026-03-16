/*
 * STM32H750VBT6 — EXTI Trigger Test
 *
 * Tests EXTI9 rising-edge detection: PB8 (output) drives 10 rising edges,
 * PB9 (input) is connected to EXTI9. Each edge polled via EXTI_RPR1.
 *
 * Error bits in error_code:
 *   bit 0: ERR_EXTI_INIT — fewer than 10 edges detected; detail0 = actual count
 *
 * On PASS detail0 = 10, then increments each ms tick.
 *
 * H750 EXTI register layout (RM0433 §20):
 *   EXTI_BASE   = 0x58000000  (APB4, D3 domain)
 *   EXTI_RTSR1  = EXTI_BASE + 0x00   rising trigger select
 *   EXTI_RPR1   = EXTI_BASE + 0x0C   rising pending register (H7-specific)
 *
 * SYSCFG_BASE = 0x58000400
 * RCC_APB4ENR at RCC_BASE+0x0F4, bit 1 = SYSCFGEN
 */

#define AEL_MAILBOX_ADDR  0x38000000u
#include "../ael_mailbox.h"

/* ---- RCC (RM0433 §8) ---------------------------------------------------- */

#define RCC_BASE              0x58024400u
#define RCC_AHB4ENR           (*(volatile uint32_t *)(RCC_BASE + 0x0E0u))
#define RCC_APB4ENR           (*(volatile uint32_t *)(RCC_BASE + 0x0F4u))
#define RCC_AHB4ENR_GPIOBEN   (1u << 1)
#define RCC_APB4ENR_SYSCFGEN  (1u << 1)

/* ---- GPIOB (RM0433 §10, base 0x58020400) -------------------------------- */

#define GPIOB_BASE   0x58020400u
#define GPIOB_MODER  (*(volatile uint32_t *)(GPIOB_BASE + 0x00u))
#define GPIOB_IDR    (*(volatile uint32_t *)(GPIOB_BASE + 0x10u))
#define GPIOB_ODR    (*(volatile uint32_t *)(GPIOB_BASE + 0x14u))

/* ---- SYSCFG (RM0433 §12, base 0x58000400) ------------------------------- */

#define SYSCFG_BASE       0x58000400u
/* EXTICR3 controls EXTI8..EXTI11; EXTI9 is bits [5:4] = 01 for PORTB */
#define SYSCFG_EXTICR3    (*(volatile uint32_t *)(SYSCFG_BASE + 0x14u))

/* ---- EXTI (RM0433 §20, H7 layout, base 0x58000000) ---------------------- */

#define EXTI_BASE    0x58000000u
#define EXTI_RTSR1   (*(volatile uint32_t *)(EXTI_BASE + 0x00u))
#define EXTI_RPR1    (*(volatile uint32_t *)(EXTI_BASE + 0x0Cu))  /* H7 rising pending */

/* ---- SysTick (ARMv7-M ARM) ---------------------------------------------- */

#define SYST_CSR        (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR        (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR        (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

/* ---- Helpers ------------------------------------------------------------ */

static void delay_ticks(uint32_t ticks)
{
    for (volatile uint32_t i = 0u; i < ticks; i++) {
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

/* Small busy delay (not tick-based) for GPIO settling */
static void busy_delay(volatile uint32_t n)
{
    while (n--) { __asm__ volatile ("nop"); }
}

/* ---- Main --------------------------------------------------------------- */

int main(void)
{
    /* SysTick: processor clock (64 MHz HSI), RVR=63999 → 1 ms/tick */
    SYST_RVR = 63999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    /* Enable GPIOB and SYSCFG clocks */
    RCC_AHB4ENR |= RCC_AHB4ENR_GPIOBEN;
    (void)RCC_AHB4ENR;
    RCC_APB4ENR |= RCC_APB4ENR_SYSCFGEN;
    (void)RCC_APB4ENR;

    ael_mailbox_init();

    /* PB8: output push-pull (MODER bits [17:16] = 01) */
    GPIOB_MODER &= ~(0x3u << 16u);
    GPIOB_MODER |=  (0x1u << 16u);

    /* PB9: input floating (MODER bits [19:18] = 00) */
    GPIOB_MODER &= ~(0x3u << 18u);

    /* Start with PB8 low */
    GPIOB_ODR &= ~(1u << 8u);

    /* SYSCFG_EXTICR3: select PORTB for EXTI9 (bits [5:4] = 01) */
    SYSCFG_EXTICR3 &= ~(0x3u << 4u);
    SYSCFG_EXTICR3 |=  (0x1u << 4u);

    /* EXTI9: enable rising-edge trigger */
    EXTI_RTSR1 |= (1u << 9u);

    /* Clear any stale pending bit */
    EXTI_RPR1 = (1u << 9u);

    uint32_t edge_count = 0u;

    for (uint32_t i = 0u; i < 10u; i++) {
        /* Ensure line is low before rising edge */
        GPIOB_ODR &= ~(1u << 8u);
        busy_delay(100u);

        /* Generate rising edge */
        GPIOB_ODR |= (1u << 8u);

        /* Poll EXTI_RPR1 bit 9 with timeout */
        uint32_t timeout = 100000u;
        while ((EXTI_RPR1 & (1u << 9u)) == 0u) {
            if (--timeout == 0u) { break; }
        }

        if (EXTI_RPR1 & (1u << 9u)) {
            edge_count++;
            /* Clear pending by writing 1 */
            EXTI_RPR1 = (1u << 9u);
        }

        busy_delay(100u);
    }

    if (edge_count == 10u) {
        ael_mailbox_pass();
        uint32_t iteration = edge_count;   /* starts at 10 */
        while (1) {
            delay_ticks(1u);
            iteration++;
            AEL_MAILBOX->detail0 = iteration;
        }
    } else {
        ael_mailbox_fail(1u, edge_count);
        while (1) {}
    }
}
