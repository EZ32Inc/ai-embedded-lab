#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x20004C00u
#include "../ael_mailbox.h"

#define RCC_BASE 0x40021000u
#define RCC_APB2ENR (*(volatile uint32_t *)(RCC_BASE + 0x18u))

#define GPIOA_BASE 0x40010800u
#define GPIOA_CRL (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_ODR (*(volatile uint32_t *)(GPIOA_BASE + 0x0Cu))

#define GPIOC_BASE 0x40011000u
#define GPIOC_CRH (*(volatile uint32_t *)(GPIOC_BASE + 0x04u))
#define GPIOC_ODR (*(volatile uint32_t *)(GPIOC_BASE + 0x0Cu))

#define RCC_IOPAEN (1u << 2)
#define RCC_IOPCEN (1u << 4)

#define GPIOA_SELFTEST_MASK ((1u << 4) | (1u << 5) | (1u << 6) | (1u << 7))
#define GPIOC_LED_MASK (1u << 13)

static void delay_cycles(uint32_t count)
{
    while (count-- > 0u) {
        __asm__ volatile ("nop");
    }
}

static uint32_t verify_pattern(uint32_t expected_a, uint32_t expected_c)
{
    uint32_t odr_a = GPIOA_ODR & GPIOA_SELFTEST_MASK;
    uint32_t odr_c = GPIOC_ODR & GPIOC_LED_MASK;

    if (odr_a != expected_a) {
        return 0xA001u | ((odr_a >> 4) << 16);
    }
    if (odr_c != expected_c) {
        return 0xC001u;
    }
    return 0u;
}

int main(void)
{
    const uint32_t patterns[] = {
        0u,
        (1u << 4) | (1u << 6),
        (1u << 5) | (1u << 7),
        GPIOA_SELFTEST_MASK,
    };
    const uint32_t led_patterns[] = {
        0u,
        0u,
        GPIOC_LED_MASK,
        GPIOC_LED_MASK,
    };

    RCC_APB2ENR |= (RCC_IOPAEN | RCC_IOPCEN);

    GPIOA_CRL &= ~((0xFu << 16) | (0xFu << 20) | (0xFu << 24) | (0xFu << 28));
    GPIOA_CRL |= ((0x3u << 16) | (0x3u << 20) | (0x3u << 24) | (0x3u << 28));

    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x2u << 20);

    ael_mailbox_init();

    for (uint32_t i = 0; i < (sizeof(patterns) / sizeof(patterns[0])); ++i) {
        const uint32_t expected_a = patterns[i];
        const uint32_t expected_c = led_patterns[i];
        uint32_t err;

        GPIOA_ODR = (GPIOA_ODR & ~GPIOA_SELFTEST_MASK) | expected_a;
        GPIOC_ODR = (GPIOC_ODR & ~GPIOC_LED_MASK) | expected_c;

        err = verify_pattern(expected_a, expected_c);
        if (err != 0u) {
            ael_mailbox_fail(err, i);
            while (1) {
            }
        }
    }

    ael_mailbox_pass();

    GPIOC_ODR |= GPIOC_LED_MASK;

    while (1) {
        AEL_MAILBOX->detail0++;
        delay_cycles(800000u);
    }
}
