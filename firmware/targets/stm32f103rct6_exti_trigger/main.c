/*
 * STM32F103RCT6 — AEL EXTI trigger test
 *
 * Observable behaviour:
 *   - PB8 (output push-pull) drives 10 rising edges
 *   - PB9 → EXTI9 (rising edge interrupt)
 *   - PASS after 10 EXTI9 interrupts
 *   - detail0 = interrupt count
 *
 * Wiring required: PB8 → PB9
 * Mailbox address: 0x2000BC00
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2000BC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE        0x40021000U
#define RCC_APB2ENR     (*(volatile uint32_t *)(RCC_BASE + 0x18U))

/* AFIO */
#define AFIO_BASE       0x40010000U
#define AFIO_EXTICR3    (*(volatile uint32_t *)(AFIO_BASE + 0x10U))

/* EXTI */
#define EXTI_BASE       0x40010400U
#define EXTI_IMR        (*(volatile uint32_t *)(EXTI_BASE + 0x00U))
#define EXTI_RTSR       (*(volatile uint32_t *)(EXTI_BASE + 0x08U))
#define EXTI_PR         (*(volatile uint32_t *)(EXTI_BASE + 0x14U))

/* GPIOB */
#define GPIOB_BASE      0x40010C00U
#define GPIOB_CRH       (*(volatile uint32_t *)(GPIOB_BASE + 0x04U))
#define GPIOB_ODR       (*(volatile uint32_t *)(GPIOB_BASE + 0x0CU))

/* NVIC */
#define NVIC_ISER0      (*(volatile uint32_t *)0xE000E100U)

static volatile uint32_t exti_count  = 0U;
static volatile uint32_t test_passed = 0U;

void EXTI9_5_IRQHandler(void)
{
    if (EXTI_PR & (1U << 9)) {
        EXTI_PR = (1U << 9);   /* clear pending */
        exti_count++;
        AEL_MAILBOX->detail0 = exti_count;
        if (exti_count >= 10U && !test_passed) {
            ael_mailbox_pass();
            test_passed = 1U;
        }
    }
}

static void delay(volatile uint32_t n)
{
    while (n--) __asm__ volatile ("nop");
}

int main(void)
{
    /* Enable GPIOB + AFIO clocks (APB2 bits 3 and 0) */
    RCC_APB2ENR |= (1U << 3) | (1U << 0);

    /*
     * PB8: output push-pull 50 MHz → CRH[3:0]  = 0x3 (CNF=00,MODE=11)
     * PB9: input floating           → CRH[7:4]  = 0x4 (CNF=01,MODE=00)
     */
    GPIOB_CRH &= ~0xFFU;
    GPIOB_CRH |=  0x43U;

    /* AFIO_EXTICR3 bits [7:4] = 0x1 → PB9 drives EXTI9 */
    AFIO_EXTICR3 &= ~(0xFU << 4);
    AFIO_EXTICR3 |=  (0x1U << 4);

    /* Enable EXTI9 rising edge */
    EXTI_IMR  |= (1U << 9);
    EXTI_RTSR |= (1U << 9);

    /* NVIC: EXTI9_5 = IRQ 23 */
    NVIC_ISER0 = (1U << 23);

    ael_mailbox_init();

    /* Drive 10 rising edges on PB8 */
    for (uint32_t i = 0U; i < 10U; i++) {
        GPIOB_ODR &= ~(1U << 8);
        delay(8000U);
        GPIOB_ODR |=  (1U << 8);
        delay(8000U);
    }

    /* Wait for ISR to declare PASS (should be near-instant) */
    while (!test_passed) {}

    while (1) {}

    return 0;
}
