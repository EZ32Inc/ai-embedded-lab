/*
 * STM32F401RCT6 — EXTI Trigger Test
 *
 * PA8 (output) generates 10 rising edges.
 * EXTI6 on PA6 (input) detects each edge via EXTI_PR polling.
 *
 * Tests the interrupt-controller path (NVIC+EXTI routing) independently
 * of simple GPIO IDR polling.
 *
 * Mailbox at 0x2000FC00.
 *   PASS: all 10 edges detected. detail0 increments each ms (heartbeat).
 *   FAIL: error_code bit0 = ERR_EXTI_MISS. detail0 = edges detected (0-9).
 *
 * Register addresses: RM0368 (STM32F401 Reference Manual).
 * Clock: 16 MHz HSI, SysTick 1 kHz.
 */

#include <stdint.h>
#include "ael_mailbox.h"

/* ---- RCC ---------------------------------------------------------------- */
#define RCC_BASE           0x40023800u
#define RCC_AHB1ENR        (*(volatile uint32_t *)(RCC_BASE + 0x30u))
#define RCC_APB2ENR        (*(volatile uint32_t *)(RCC_BASE + 0x44u))
#define RCC_AHB1ENR_GPIOAEN  (1u << 0)
#define RCC_APB2ENR_SYSCFGEN (1u << 14)

/* ---- GPIOA -------------------------------------------------------------- */
#define GPIOA_BASE  0x40020000u
#define GPIOA_MODER (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_ODR   (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))

/* ---- SYSCFG ------------------------------------------------------------- */
#define SYSCFG_BASE    0x40013800u
#define SYSCFG_EXTICR2 (*(volatile uint32_t *)(SYSCFG_BASE + 0x0Cu))

/* ---- EXTI --------------------------------------------------------------- */
#define EXTI_BASE  0x40013C00u
#define EXTI_IMR   (*(volatile uint32_t *)(EXTI_BASE + 0x00u))
#define EXTI_RTSR  (*(volatile uint32_t *)(EXTI_BASE + 0x08u))
#define EXTI_PR    (*(volatile uint32_t *)(EXTI_BASE + 0x14u))

/* ---- SysTick ------------------------------------------------------------ */
#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

#define ERR_EXTI_MISS (1u << 0)

#define PULSE_COUNT 10u
#define PULSE_TIMEOUT 100000u   /* poll iterations before giving up */

static void delay_ms(uint32_t ms)
{
    for (uint32_t i = 0u; i < ms; i++) {
        SYST_CVR = 0u;
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

int main(void)
{
    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    /* Enable GPIOA and SYSCFG clocks */
    RCC_AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    (void)RCC_AHB1ENR;
    RCC_APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    (void)RCC_APB2ENR;

    /* PA8: output push-pull (MODER[17:16]=01) */
    GPIOA_MODER &= ~(0x3u << 16u);
    GPIOA_MODER |=  (0x1u << 16u);
    GPIOA_ODR   &= ~(1u << 8u);    /* start LOW */

    /* PA6: input floating (MODER[13:12]=00) */
    GPIOA_MODER &= ~(0x3u << 12u);

    /*
     * Route EXTI6 to PORTA.
     * SYSCFG_EXTICR2 bits [11:8] = EXTI6, value 0b0000 = PA.
     */
    SYSCFG_EXTICR2 &= ~(0xFu << 8u);   /* select PA for EXTI6 */

    /* Configure EXTI6: rising edge trigger, unmask */
    EXTI_RTSR |= (1u << 6u);
    EXTI_IMR  |= (1u << 6u);

    ael_mailbox_init();

    uint32_t detected = 0u;
    uint32_t err = 0u;

    for (uint32_t pulse = 0u; pulse < PULSE_COUNT; pulse++) {
        /* Ensure line is LOW before each pulse */
        GPIOA_ODR &= ~(1u << 8u);
        delay_ms(1u);

        /* Clear any stale pending bit */
        EXTI_PR = (1u << 6u);

        /* Rising edge: PA8 LOW → HIGH */
        GPIOA_ODR |= (1u << 8u);

        /* Poll EXTI_PR bit 6 with timeout */
        uint32_t timeout = PULSE_TIMEOUT;
        while ((EXTI_PR & (1u << 6u)) == 0u) {
            if (--timeout == 0u) { err |= ERR_EXTI_MISS; goto done; }
        }
        /* Clear pending by writing 1 */
        EXTI_PR = (1u << 6u);
        detected++;
    }

done:
    if (err == 0u) {
        ael_mailbox_pass();
        uint32_t iteration = 0u;
        while (1) {
            delay_ms(1u);
            AEL_MAILBOX->detail0 = ++iteration;
        }
    } else {
        ael_mailbox_fail(err, detected);
        while (1) {}
    }
}
