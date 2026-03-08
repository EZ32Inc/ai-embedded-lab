#include <stdint.h>

#define RCC_BASE 0x40021000
#define RCC_APB2ENR (*(volatile uint32_t *)(RCC_BASE + 0x18))

#define GPIOA_BASE 0x40010800
#define GPIOA_CRL (*(volatile uint32_t *)(GPIOA_BASE + 0x00))
#define GPIOA_ODR (*(volatile uint32_t *)(GPIOA_BASE + 0x0C))

#define GPIOC_BASE 0x40011000
#define GPIOC_CRH (*(volatile uint32_t *)(GPIOC_BASE + 0x04))
#define GPIOC_ODR (*(volatile uint32_t *)(GPIOC_BASE + 0x0C))

#define RCC_IOPAEN (1u << 2)
#define RCC_IOPCEN (1u << 4)

int main(void) {
    // Enable GPIOA and GPIOC clocks
    RCC_APB2ENR |= (RCC_IOPAEN | RCC_IOPCEN);

    // Configure PA4..PA7 as output push-pull 50MHz (MODE=11, CNF=00)
    // Each pin uses 4 bits in CRL. Clear bits for PA4-PA7 then set to 0b0011.
    GPIOA_CRL &= ~(0xFFFFu << 16);
    GPIOA_CRL |= (0x3333u << 16);

    // Configure PC13 as output push-pull 2MHz (MODE=10, CNF=00)
    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x2u << 20);

    uint32_t div0 = 0;
    uint32_t div1 = 0;
    uint32_t div2 = 0;
    uint32_t div3 = 0;
    uint32_t led_div = 0;
    while (1) {
        // Distinct toggle rates for PA4..PA7
        if (++div0 >= 200) { // fastest
            div0 = 0;
            GPIOA_ODR ^= (1u << 4);
        }
        if (++div1 >= 400) {
            div1 = 0;
            GPIOA_ODR ^= (1u << 5);
        }
        if (++div2 >= 600) {
            div2 = 0;
            GPIOA_ODR ^= (1u << 6);
        }
        if (++div3 >= 800) {
            div3 = 0;
            GPIOA_ODR ^= (1u << 7);
        }

        // Blink PC13 at a slower rate.
        if (++led_div >= 16380) { // ~5x slower than previous
            led_div = 0;
            GPIOC_ODR ^= (1u << 13);
        }
    }
}
