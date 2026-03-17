/*
 * STM32F103RCT6 — AEL GPIO loopback test
 *
 * Observable behaviour:
 *   - PB0 (output push-pull) drives high/low
 *   - PB1 (input floating) reads back
 *   - PASS after 10 successful high+low cycles
 *   - detail0 = pass_count, increments after PASS
 *
 * Wiring required: PB0 → PB1
 * Mailbox address: 0x2000BC00
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2000BC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE        0x40021000U
#define RCC_APB2ENR     (*(volatile uint32_t *)(RCC_BASE + 0x18U))

/* GPIOB (APB2) */
#define GPIOB_BASE      0x40010C00U
#define GPIOB_CRL       (*(volatile uint32_t *)(GPIOB_BASE + 0x00U))
#define GPIOB_IDR       (*(volatile uint32_t *)(GPIOB_BASE + 0x08U))
#define GPIOB_ODR       (*(volatile uint32_t *)(GPIOB_BASE + 0x0CU))

static void delay(volatile uint32_t n)
{
    while (n--) __asm__ volatile ("nop");
}

int main(void)
{
    /* Enable GPIOB clock (APB2 bit 3) */
    RCC_APB2ENR |= (1U << 3);

    /*
     * PB0: output push-pull 50 MHz → CRL[3:0] = 0x3 (CNF=00,MODE=11)
     * PB1: input floating         → CRL[7:4] = 0x4 (CNF=01,MODE=00)
     */
    GPIOB_CRL &= ~0xFFU;
    GPIOB_CRL |=  0x43U;

    ael_mailbox_init();

    uint32_t pass_count = 0U;

    while (1) {
        /* Drive PB0 high */
        GPIOB_ODR |= (1U << 0);
        delay(4000U);
        if (!(GPIOB_IDR & (1U << 1))) {
            ael_mailbox_fail(0x01U, 0U);
            while (1) {}
        }

        /* Drive PB0 low */
        GPIOB_ODR &= ~(1U << 0);
        delay(4000U);
        if (GPIOB_IDR & (1U << 1)) {
            ael_mailbox_fail(0x02U, 0U);
            while (1) {}
        }

        pass_count++;
        AEL_MAILBOX->detail0 = pass_count;

        if (pass_count >= 10U) {
            ael_mailbox_pass();
            while (1) {
                delay(4000U);
                AEL_MAILBOX->detail0++;
            }
        }
    }

    return 0;
}
