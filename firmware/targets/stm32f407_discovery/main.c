/*
 * STM32F4 Discovery — AEL validation firmware
 *
 * Observable behaviour:
 *   - PD12 (green LED) blinks at ~1 Hz
 *   - AEL mailbox at 0x2001FC00 reports PASS after first blink cycle
 *   - blink_count increments each cycle — easy GDB inspection
 *
 * GDB breakpoint targets: main(), blink_on(), blink_off()
 * Mailbox address: 0x2001FC00 (top of 128 KB SRAM1, 1 KB from end)
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2001FC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE        0x40023800U
#define RCC_AHB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x30U))

/* GPIOD */
#define GPIOD_BASE      0x40020C00U
#define GPIOD_MODER     (*(volatile uint32_t *)(GPIOD_BASE + 0x00U))
#define GPIOD_ODR       (*(volatile uint32_t *)(GPIOD_BASE + 0x14U))

/* Discovery LEDs: PD12=green, PD13=orange, PD14=red, PD15=blue */
#define LED_GREEN   (1U << 12)

/* ~100 ms delay at 16 MHz HSI (4 cycles/iteration) */
#define DELAY_100MS  400000U

volatile uint32_t blink_count = 0;  /* inspect in GDB: p blink_count */

static void delay(uint32_t count)
{
    while (count--) {
        __asm__ volatile ("nop");
    }
}

void blink_on(void)
{
    GPIOD_ODR |= LED_GREEN;
}

void blink_off(void)
{
    GPIOD_ODR &= ~LED_GREEN;
}

int main(void)
{
    /* Enable GPIOD clock */
    RCC_AHB1ENR |= (1U << 3);

    /* PD12–PD15: output push-pull */
    GPIOD_MODER &= ~(0xFFU << 24);
    GPIOD_MODER |=  (0x55U << 24);

    /* Init mailbox: RUNNING */
    ael_mailbox_init();

    while (1) {
        blink_on();
        delay(5U * DELAY_100MS);
        blink_off();
        delay(5U * DELAY_100MS);

        blink_count++;

        /* After first complete blink cycle: PASS */
        if (blink_count == 1U) {
            ael_mailbox_pass();
        }

        /* Update loop counter in detail0 */
        AEL_MAILBOX->detail0 = blink_count;
    }

    return 0;
}
