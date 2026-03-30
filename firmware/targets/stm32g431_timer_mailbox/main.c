#include <stdint.h>
#include "../ael_mailbox.h"

/* STM32G431 — RCC on APB1 */
#define RCC_BASE       0x40021000u
#define RCC_APB1ENR1   (*(volatile uint32_t *)(RCC_BASE + 0x58u))

/* TIM3 on APB1 — same base as STM32F4 */
#define TIM3_BASE      0x40000400u
#define TIM3_CR1       (*(volatile uint32_t *)(TIM3_BASE + 0x00u))
#define TIM3_DIER      (*(volatile uint32_t *)(TIM3_BASE + 0x0Cu))
#define TIM3_SR        (*(volatile uint32_t *)(TIM3_BASE + 0x10u))
#define TIM3_EGR       (*(volatile uint32_t *)(TIM3_BASE + 0x14u))
#define TIM3_PSC       (*(volatile uint32_t *)(TIM3_BASE + 0x28u))
#define TIM3_ARR       (*(volatile uint32_t *)(TIM3_BASE + 0x2Cu))

#define TIM_CR1_CEN    (1u << 0)
#define TIM_DIER_UIE   (1u << 0)
#define TIM_SR_UIF     (1u << 0)

/* NVIC: TIM3 = IRQ 29, ISER0 bit 29 */
#define NVIC_ISER0     (*(volatile uint32_t *)0xE000E100u)

static volatile uint32_t tim3_irq_count = 0u;
static volatile uint32_t test_passed = 0u;

void TIM3_IRQHandler(void)
{
    if ((TIM3_SR & TIM_SR_UIF) == 0u) {
        return;
    }

    TIM3_SR &= ~TIM_SR_UIF;
    tim3_irq_count++;
    AEL_MAILBOX->detail0 = tim3_irq_count;

    if (tim3_irq_count >= 10u && !test_passed) {
        ael_mailbox_pass();
        test_passed = 1u;
    }
}

int main(void)
{
    ael_mailbox_init();

    /* Enable TIM3 clock on APB1ENR1 (bit 1). */
    RCC_APB1ENR1 |= (1u << 1);
    (void)RCC_APB1ENR1;

    /*
     * 16 MHz HSI / 16000 / 100 = 10 Hz
     * → one interrupt every 100 ms
     * → PASS after 10 interrupts (~1 s)
     */
    TIM3_PSC = 15999u;
    TIM3_ARR = 99u;
    TIM3_EGR = 1u;
    TIM3_SR = 0u;
    TIM3_DIER = TIM_DIER_UIE;
    TIM3_CR1 = TIM_CR1_CEN;

    NVIC_ISER0 = (1u << 29);

    while (!test_passed) {
        __asm__ volatile ("wfi");
    }

    while (1) {
        __asm__ volatile ("wfi");
    }
}
