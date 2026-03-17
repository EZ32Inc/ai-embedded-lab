/*
 * STM32F407 Discovery — AEL TIM3 timer interrupt test
 *
 * Observable behaviour:
 *   - TIM3 fires update interrupt at ~100 ms intervals (PSC=15999, ARR=100, 16 MHz HSI)
 *   - PASS after 10 interrupts (~1 second elapsed)
 *   - detail0 = interrupt count (increments in ISR, continues after PASS)
 *
 * No external wiring required. Exercises: RCC, TIM3, NVIC, interrupt delivery.
 * Mailbox address: 0x2001FC00 (SRAM1 top -1 KB)
 *
 * GDB breakpoint targets: TIM3_IRQHandler(), main()
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2001FC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE       0x40023800U
#define RCC_APB1ENR    (*(volatile uint32_t *)(RCC_BASE + 0x40U))

/* TIM3 on APB1 */
#define TIM3_BASE      0x40000400U
#define TIM3_CR1       (*(volatile uint32_t *)(TIM3_BASE + 0x00U))
#define TIM3_DIER      (*(volatile uint32_t *)(TIM3_BASE + 0x0CU))
#define TIM3_SR        (*(volatile uint32_t *)(TIM3_BASE + 0x10U))
#define TIM3_PSC       (*(volatile uint32_t *)(TIM3_BASE + 0x28U))
#define TIM3_ARR       (*(volatile uint32_t *)(TIM3_BASE + 0x2CU))

#define TIM3_CR1_CEN   (1U << 0)
#define TIM3_DIER_UIE  (1U << 0)
#define TIM3_SR_UIF    (1U << 0)

/* NVIC: TIM3 = IRQ 29, ISER0 bit 29 */
#define NVIC_ISER0     (*(volatile uint32_t *)0xE000E100U)

volatile uint32_t tim3_irq_count = 0;
volatile uint32_t test_passed    = 0;

void TIM3_IRQHandler(void)
{
    if (TIM3_SR & TIM3_SR_UIF) {
        TIM3_SR &= ~TIM3_SR_UIF;   /* clear update interrupt flag */
        tim3_irq_count++;
        AEL_MAILBOX->detail0 = tim3_irq_count;

        if (tim3_irq_count >= 10U && !test_passed) {
            ael_mailbox_pass();
            test_passed = 1U;
        }
    }
}

int main(void)
{
    /* Enable TIM3 clock on APB1 (bit 1) */
    RCC_APB1ENR |= (1U << 1);

    ael_mailbox_init();

    /*
     * TIM3 period: 16 MHz / (PSC+1) / (ARR+1) = 16 MHz / 16000 / 101 ≈ 9.9 Hz
     * Use PSC=15999, ARR=99 → period = 16000000/16000/100 = 10 Hz (100 ms/interrupt)
     */
    TIM3_PSC  = 15999U;
    TIM3_ARR  = 99U;
    TIM3_SR   = 0U;          /* clear any pending flag before enabling */
    TIM3_DIER = TIM3_DIER_UIE;
    TIM3_CR1  = TIM3_CR1_CEN;

    /* Enable TIM3 interrupt in NVIC */
    NVIC_ISER0 = (1U << 29);

    /* Wait for PASS via interrupt (WFI to save power between interrupts) */
    while (!test_passed) {
        __asm__ volatile ("wfi");
    }

    /* Keep running; detail0 continues to increment in ISR */
    while (1) {
        __asm__ volatile ("wfi");
    }

    return 0;
}
