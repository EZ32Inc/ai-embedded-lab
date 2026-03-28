#include <stdint.h>

#define RCC_BASE 0x40021000u
#define RCC_APB2ENR (*(volatile uint32_t *)(RCC_BASE + 0x18u))

#define GPIOC_BASE 0x40011000u
#define GPIOC_CRH (*(volatile uint32_t *)(GPIOC_BASE + 0x04u))
#define GPIOC_BSRR (*(volatile uint32_t *)(GPIOC_BASE + 0x10u))

#define RCC_IOPCEN (1u << 4)

#define GPIOC_LED_MASK (1u << 13)

static void delay_cycles(uint32_t count)
{
    while (count-- > 0u) {
        __asm__ volatile ("nop");
    }
}

int main(void)
{
    RCC_APB2ENR |= RCC_IOPCEN;

    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x3u << 20);

    while (1) {
        /* Bluepill-style LED is typically active-low on PC13. */
        GPIOC_BSRR = (1u << (13u + 16u));
        delay_cycles(500000u);
        GPIOC_BSRR = GPIOC_LED_MASK;
        delay_cycles(500000u);
    }
}
