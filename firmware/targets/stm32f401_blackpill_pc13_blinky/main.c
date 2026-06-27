#include "stm32f401xe.h"

void __libc_init_array(void)
{
}

static void delay_cycles(volatile uint32_t cycles)
{
    while (cycles-- > 0u) {
        __NOP();
    }
}

static void pc13_led_init(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOCEN;
    (void)RCC->AHB1ENR;

    GPIOC->MODER &= ~(0x3u << (13u * 2u));
    GPIOC->MODER |= (0x1u << (13u * 2u));
    GPIOC->OTYPER &= ~(1u << 13u);
    GPIOC->OSPEEDR &= ~(0x3u << (13u * 2u));
    GPIOC->PUPDR &= ~(0x3u << (13u * 2u));

    GPIOC->BSRR = (1u << 13u);
}

int main(void)
{
    pc13_led_init();

    while (1) {
        GPIOC->BSRR = (1u << (13u + 16u));
        delay_cycles(800000u);
        GPIOC->BSRR = (1u << 13u);
        delay_cycles(800000u);
    }
}
