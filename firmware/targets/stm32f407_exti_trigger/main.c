/*
 * STM32F407 Discovery — AEL EXTI trigger test
 *
 * Observable behaviour:
 *   - PB8 (output) drives 10 rising edges with 1 ms low/high intervals
 *   - PB9 (input) routed via SYSCFG to EXTI9, rising-edge interrupt
 *   - PASS after all 10 EXTI9 interrupts received
 *   - detail0 = interrupt count (0→10, then WFI)
 *
 * Exercises: RCC, GPIOB, SYSCFG EXTI routing, NVIC, EXTI9_5 IRQ delivery.
 * Wiring required: PB8 → PB9 (jumper wire)
 * Mailbox address: 0x2001FC00 (SRAM1 top -1 KB)
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2001FC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE        0x40023800U
#define RCC_AHB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x30U))
#define RCC_APB2ENR     (*(volatile uint32_t *)(RCC_BASE + 0x44U))

/* GPIOB */
#define GPIOB_BASE      0x40020400U
#define GPIOB_MODER     (*(volatile uint32_t *)(GPIOB_BASE + 0x00U))
#define GPIOB_ODR       (*(volatile uint32_t *)(GPIOB_BASE + 0x14U))
#define GPIOB_PUPDR     (*(volatile uint32_t *)(GPIOB_BASE + 0x0CU))

#define PIN8  (1U << 8)
#define PIN9  (1U << 9)

/*
 * SYSCFG — routes GPIO port to EXTI line
 * EXTICR3 (offset 0x10) covers EXTI8–EXTI11, 4 bits each:
 *   [3:0]=EXTI8, [7:4]=EXTI9, [11:8]=EXTI10, [15:12]=EXTI11
 * Port B = 0x1
 */
#define SYSCFG_BASE     0x40013800U
#define SYSCFG_EXTICR3  (*(volatile uint32_t *)(SYSCFG_BASE + 0x10U))

/* EXTI */
#define EXTI_BASE       0x40013C00U
#define EXTI_IMR        (*(volatile uint32_t *)(EXTI_BASE + 0x00U))
#define EXTI_RTSR       (*(volatile uint32_t *)(EXTI_BASE + 0x08U))
#define EXTI_PR         (*(volatile uint32_t *)(EXTI_BASE + 0x14U))

/* NVIC: EXTI9_5 = IRQ 23, ISER0 bit 23 */
#define NVIC_ISER0      (*(volatile uint32_t *)0xE000E100U)

/* ~1 ms delay at 16 MHz HSI */
#define DELAY_1MS  4000U

static void delay(uint32_t count)
{
    while (count--) {
        __asm__ volatile ("nop");
    }
}

volatile uint32_t exti9_count = 0;
volatile uint32_t test_passed = 0;

void EXTI9_5_IRQHandler(void)
{
    if (EXTI_PR & PIN9) {
        EXTI_PR = PIN9;   /* clear pending bit by writing 1 */
        exti9_count++;
        AEL_MAILBOX->detail0 = exti9_count;

        if (exti9_count >= 10U && !test_passed) {
            ael_mailbox_pass();
            test_passed = 1U;
        }
    }
}

int main(void)
{
    /* Enable GPIOB and SYSCFG clocks */
    RCC_AHB1ENR |= (1U << 1);    /* GPIOB: AHB1 bit 1 */
    RCC_APB2ENR |= (1U << 14);   /* SYSCFG: APB2 bit 14 */

    /* PB8: output push-pull, start low */
    GPIOB_MODER &= ~(3U << 16);
    GPIOB_MODER |=  (1U << 16);
    GPIOB_ODR   &= ~PIN8;

    /* PB9: input with pull-down */
    GPIOB_MODER &= ~(3U << 18);  /* input = 00 */
    GPIOB_PUPDR &= ~(3U << 18);
    GPIOB_PUPDR |=  (2U << 18);  /* pull-down */

    /* SYSCFG EXTICR3: route EXTI9 to Port B (0x1) */
    SYSCFG_EXTICR3 &= ~(0xFU << 4);
    SYSCFG_EXTICR3 |=  (0x1U << 4);

    /* EXTI9: rising-edge trigger, unmask */
    EXTI_RTSR |= PIN9;
    EXTI_IMR  |= PIN9;
    EXTI_PR    = PIN9;   /* clear any stale pending before enabling NVIC */

    /* Enable EXTI9_5 IRQ in NVIC */
    NVIC_ISER0 = (1U << 23);

    ael_mailbox_init();

    /* Drive 10 rising edges: low → high with 1 ms per state */
    for (uint32_t i = 0; i < 10U; i++) {
        GPIOB_ODR &= ~PIN8;   /* ensure low */
        delay(DELAY_1MS);
        GPIOB_ODR |= PIN8;    /* rising edge */
        delay(DELAY_1MS);
    }
    GPIOB_ODR &= ~PIN8;       /* leave PB8 low */

    /* Wait for all 10 interrupts (with generous timeout) */
    uint32_t wait = 500000U;
    while (!test_passed && wait--) {
        __asm__ volatile ("nop");
    }

    if (!test_passed) {
        /* Timeout: not all edges were received */
        ael_mailbox_fail(0x01U, exti9_count);
    }

    while (1) {
        __asm__ volatile ("wfi");
    }

    return 0;
}
