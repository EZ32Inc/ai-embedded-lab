#include <stdint.h>

#define RCC_BASE        0x44020C00u
#define RCC_AHB2ENR     (*(volatile uint32_t *)(RCC_BASE + 0x08Cu))

#define GPIOC_BASE      0x42020800u
#define GPIOC_MODER     (*(volatile uint32_t *)(GPIOC_BASE + 0x00u))
#define GPIOC_OTYPER    (*(volatile uint32_t *)(GPIOC_BASE + 0x04u))
#define GPIOC_OSPEEDR   (*(volatile uint32_t *)(GPIOC_BASE + 0x08u))
#define GPIOC_PUPDR     (*(volatile uint32_t *)(GPIOC_BASE + 0x0Cu))
#define GPIOC_ODR       (*(volatile uint32_t *)(GPIOC_BASE + 0x14u))

#define LED_PIN 13u

static void delay(void)
{
    for (volatile uint32_t i = 0; i < 700000u; ++i) {
        __asm__ volatile ("nop");
    }
}

int main(void)
{
    RCC_AHB2ENR |= (1u << 2); /* GPIOCEN */
    (void)RCC_AHB2ENR;

    const uint32_t shift = LED_PIN * 2u;
    GPIOC_MODER = (GPIOC_MODER & ~(3u << shift)) | (1u << shift);
    GPIOC_OTYPER &= ~(1u << LED_PIN);
    GPIOC_OSPEEDR = (GPIOC_OSPEEDR & ~(3u << shift)) | (1u << shift);
    GPIOC_PUPDR &= ~(3u << shift);

    while (1) {
        GPIOC_ODR ^= (1u << LED_PIN);
        delay();
    }
}
