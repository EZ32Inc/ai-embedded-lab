/*
 * STM32F4 Discovery — minimal validation firmware
 *
 * Observable behaviour:
 *   - PD12 (green LED on Discovery board) blinks at ~1 Hz
 *   - Counter variable increments each blink — easy GDB inspection
 *
 * GDB breakpoint targets:
 *   - main()        entry point
 *   - blink_on()    LED on
 *   - blink_off()   LED off
 *
 * No HAL, no RTOS, no stdlib. Bare CMSIS registers only.
 */

#include <stdint.h>

/* RCC */
#define RCC_BASE        0x40023800U
#define RCC_AHB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x30U))

/* GPIOD */
#define GPIOD_BASE      0x40020C00U
#define GPIOD_MODER     (*(volatile uint32_t *)(GPIOD_BASE + 0x00U))
#define GPIOD_ODR       (*(volatile uint32_t *)(GPIOD_BASE + 0x14U))

/* Discovery LEDs:
 *   PD12 = green
 *   PD13 = orange
 *   PD14 = red
 *   PD15 = blue
 */
#define LED_GREEN   (1U << 12)
#define LED_ORANGE  (1U << 13)
#define LED_RED     (1U << 14)
#define LED_BLUE    (1U << 15)

/* Approximate delay at 16 MHz HSI (default reset clock).
 * Each iteration ~4 cycles → 16e6/4 = 4e6 iterations per second.
 * 400000 iterations ≈ 100 ms. */
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
    RCC_AHB1ENR |= (1U << 3);   /* GPIODEN */

    /* PD12–PD15: output push-pull (MODER = 01) */
    GPIOD_MODER &= ~(0xFFU << 24);
    GPIOD_MODER |=  (0x55U << 24);  /* 01 01 01 01 for PD12-PD15 */

    while (1) {
        blink_on();
        delay(5U * DELAY_100MS);   /* 500 ms ON */
        blink_off();
        delay(5U * DELAY_100MS);   /* 500 ms OFF */
        blink_count++;
    }

    return 0;
}
