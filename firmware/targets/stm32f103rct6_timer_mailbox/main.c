/*
 * STM32F103RCT6 — AEL TIM2 interrupt mailbox test
 *
 * Observable behaviour:
 *   - TIM2 generates interrupt every 100 ms (8 MHz HSI / 8000 / 100)
 *   - PASS after 10 interrupts (~1 s)
 *   - detail0 = interrupt count, keeps incrementing after PASS
 *
 * Wiring required: none
 * Mailbox address: 0x2000BC00
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2000BC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE        0x40021000U
#define RCC_APB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x1CU))

/* TIM2 (APB1) */
#define TIM2_BASE       0x40000000U
#define TIM2_CR1        (*(volatile uint32_t *)(TIM2_BASE + 0x00U))
#define TIM2_DIER       (*(volatile uint32_t *)(TIM2_BASE + 0x0CU))
#define TIM2_SR         (*(volatile uint32_t *)(TIM2_BASE + 0x10U))
#define TIM2_EGR        (*(volatile uint32_t *)(TIM2_BASE + 0x14U))
#define TIM2_PSC        (*(volatile uint32_t *)(TIM2_BASE + 0x28U))
#define TIM2_ARR        (*(volatile uint32_t *)(TIM2_BASE + 0x2CU))

/* NVIC */
#define NVIC_ISER0      (*(volatile uint32_t *)0xE000E100U)

static volatile uint32_t tim2_irq_count = 0U;
static volatile uint32_t test_passed    = 0U;

void TIM2_IRQHandler(void)
{
    if (TIM2_SR & 1U) {                /* UIF */
        TIM2_SR &= ~1U;
        tim2_irq_count++;
        AEL_MAILBOX->detail0 = tim2_irq_count;
        if (tim2_irq_count >= 10U && !test_passed) {
            ael_mailbox_pass();
            test_passed = 1U;
        }
    }
}

int main(void)
{
    /* Enable TIM2 clock (APB1 bit 0) */
    RCC_APB1ENR |= (1U << 0);

    ael_mailbox_init();

    /* TIM2: PSC=7999, ARR=99 → 8 MHz / 8000 / 100 = 10 Hz (100 ms) */
    TIM2_PSC  = 7999U;
    TIM2_ARR  = 99U;
    TIM2_EGR  = 1U;    /* UG: force shadow register load before CEN */
    TIM2_SR   = 0U;    /* clear UIF that UG just set */
    TIM2_DIER = 1U;    /* UIE */
    TIM2_CR1  = 1U;    /* CEN */

    /* NVIC: TIM2 = IRQ 28 */
    NVIC_ISER0 = (1U << 28);

    while (1) {}

    return 0;
}
