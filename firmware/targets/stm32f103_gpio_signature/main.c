#include <stdint.h>

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

int main(void) {
    RCC_APB2ENR |= (RCC_IOPAEN | RCC_IOPCEN);

    /* PA4 and PA5 are machine-observed outputs. */
    GPIOA_CRL &= ~((0xFu << 16) | (0xFu << 20));
    GPIOA_CRL |= ((0x3u << 16) | (0x3u << 20));

    /* PC13 remains the operator-visible heartbeat. */
    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x2u << 20);
    GPIOC_ODR |= (1u << 13);

    uint32_t counter = 0u;
    uint32_t led_div = 0u;

    while (1) {
        uint32_t odr = GPIOA_ODR & ~((1u << 4) | (1u << 5));
        counter += 1u;
        if ((counter & 0x1u) != 0u) {
            odr |= (1u << 4);
        }
        if ((counter & 0x2u) != 0u) {
            odr |= (1u << 5);
        }
        GPIOA_ODR = odr;

        led_div += 1u;
        if (led_div >= 1000000u) {
            led_div = 0u;
            GPIOC_ODR ^= (1u << 13);
        }
    }
}
