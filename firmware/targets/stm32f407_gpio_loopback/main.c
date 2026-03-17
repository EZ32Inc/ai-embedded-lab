/*
 * STM32F407 Discovery — AEL GPIO loopback test
 *
 * Observable behaviour:
 *   - PB0 (output) drives high/low, PB1 (input) reads back via loopback wire
 *   - 10 successful round-trip cycles required for PASS
 *   - detail0 = pass_count (increments each successful cycle, keeps going after PASS)
 *
 * Wiring required: PB0 → PB1 (jumper wire)
 * Mailbox address: 0x2001FC00 (SRAM1 top -1 KB)
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2001FC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE      0x40023800U
#define RCC_AHB1ENR   (*(volatile uint32_t *)(RCC_BASE + 0x30U))

/* GPIOB */
#define GPIOB_BASE    0x40020400U
#define GPIOB_MODER   (*(volatile uint32_t *)(GPIOB_BASE + 0x00U))
#define GPIOB_ODR     (*(volatile uint32_t *)(GPIOB_BASE + 0x14U))
#define GPIOB_IDR     (*(volatile uint32_t *)(GPIOB_BASE + 0x10U))
#define GPIOB_PUPDR   (*(volatile uint32_t *)(GPIOB_BASE + 0x0CU))

#define PIN0  (1U << 0)
#define PIN1  (1U << 1)

/* ~1 ms delay at 16 MHz HSI (4 cycles/iter) */
#define DELAY_1MS  4000U

static void delay(uint32_t count)
{
    while (count--) {
        __asm__ volatile ("nop");
    }
}

int main(void)
{
    /* Enable GPIOB clock */
    RCC_AHB1ENR |= (1U << 1);

    /* PB0: output push-pull */
    GPIOB_MODER &= ~(3U << 0);
    GPIOB_MODER |=  (1U << 0);

    /* PB1: input with pull-down (default low when PB0 is low) */
    GPIOB_MODER &= ~(3U << 2);   /* input = 00 */
    GPIOB_PUPDR &= ~(3U << 2);
    GPIOB_PUPDR |=  (2U << 2);   /* pull-down */

    ael_mailbox_init();

    uint32_t pass_count = 0;

    while (1) {
        /* Drive PB0 high, wait, read PB1 — expect 1 */
        GPIOB_ODR |= PIN0;
        delay(DELAY_1MS);
        uint32_t high_ok = (GPIOB_IDR & PIN1) ? 1U : 0U;

        /* Drive PB0 low, wait, read PB1 — expect 0 */
        GPIOB_ODR &= ~PIN0;
        delay(DELAY_1MS);
        uint32_t low_ok = (GPIOB_IDR & PIN1) ? 0U : 1U;

        if (!high_ok || !low_ok) {
            /* Loopback mismatch — 0x01=high read fail, 0x02=low read fail */
            ael_mailbox_fail(high_ok ? 0x02U : 0x01U, pass_count);
            while (1) {}
        }

        pass_count++;
        AEL_MAILBOX->detail0 = pass_count;

        if (pass_count >= 10U) {
            ael_mailbox_pass();
            /* Keep incrementing detail0 to show liveness after PASS */
            while (1) {
                delay(DELAY_1MS);
                AEL_MAILBOX->detail0++;
            }
        }
    }

    return 0;
}
