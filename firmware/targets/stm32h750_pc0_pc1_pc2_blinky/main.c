/*
 * STM32H750 PC0/PC1/PC2 LED blink.
 *
 * Clock: reset-default 64 MHz HSI. SysTick is configured for 1 ms ticks.
 * GPIOC is on the H7 AHB4 bus. PC0 blinks; PC1 and PC2 stay high/off.
 */

#include <stdint.h>

#define RCC_BASE              0x58024400u
#define RCC_AHB4ENR           (*(volatile uint32_t *)(RCC_BASE + 0x0E0u))
#define RCC_AHB4ENR_GPIOCEN   (1u << 2)

#define GPIOC_BASE            0x58020800u
#define GPIOC_MODER           (*(volatile uint32_t *)(GPIOC_BASE + 0x00u))
#define GPIOC_OTYPER          (*(volatile uint32_t *)(GPIOC_BASE + 0x04u))
#define GPIOC_OSPEEDR         (*(volatile uint32_t *)(GPIOC_BASE + 0x08u))
#define GPIOC_PUPDR           (*(volatile uint32_t *)(GPIOC_BASE + 0x0Cu))
#define GPIOC_BSRR            (*(volatile uint32_t *)(GPIOC_BASE + 0x18u))

#define SYST_CSR              (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR              (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR              (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE       (1u << 0)
#define SYST_CSR_CLKSOURCE    (1u << 2)
#define SYST_CSR_COUNTFLAG    (1u << 16)

#define LED0_MASK             (1u << 0)
#define LED_OFF_MASK          ((1u << 1) | (1u << 2))
#define LED_MASK              (LED0_MASK | LED_OFF_MASK)

static void delay_ms(uint32_t ms)
{
    for (uint32_t i = 0u; i < ms; i++) {
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

int main(void)
{
    SYST_RVR = 63999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    RCC_AHB4ENR |= RCC_AHB4ENR_GPIOCEN;
    (void)RCC_AHB4ENR;

    GPIOC_MODER &= ~((0x3u << 0u) | (0x3u << 2u) | (0x3u << 4u));
    GPIOC_MODER |=  ((0x1u << 0u) | (0x1u << 2u) | (0x1u << 4u));
    GPIOC_OTYPER &= ~LED_MASK;
    GPIOC_OSPEEDR &= ~((0x3u << 0u) | (0x3u << 2u) | (0x3u << 4u));
    GPIOC_PUPDR &= ~((0x3u << 0u) | (0x3u << 2u) | (0x3u << 4u));

    GPIOC_BSRR = LED_MASK;

    while (1) {
        GPIOC_BSRR = (LED0_MASK << 16u) | LED_OFF_MASK;
        delay_ms(500u);
        GPIOC_BSRR = LED_MASK;
        delay_ms(500u);
    }
}
