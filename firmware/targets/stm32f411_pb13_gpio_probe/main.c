#include "stm32f411xe.h"

void __libc_init_array(void) {
}

static void gpio_set_output(GPIO_TypeDef *gpio, uint32_t pin) {
    const uint32_t shift = pin * 2u;
    gpio->MODER &= ~(0x3u << shift);
    gpio->MODER |= (0x1u << shift);
    gpio->OTYPER &= ~(1u << pin);
    gpio->OSPEEDR |= (0x3u << shift);
    gpio->PUPDR &= ~(0x3u << shift);
}

int main(void) {
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOBEN | RCC_AHB1ENR_GPIOCEN;
    (void)RCC->AHB1ENR;

    gpio_set_output(GPIOA, 2u);
    gpio_set_output(GPIOA, 3u);
    gpio_set_output(GPIOB, 13u);
    gpio_set_output(GPIOC, 13u);

    GPIOA->ODR &= ~((1u << 2) | (1u << 3));
    GPIOB->ODR &= ~(1u << 13);
    GPIOC->ODR |= (1u << 13);

    while (1) {
        for (volatile uint32_t i = 0u; i < 200u; ++i) {
            __asm__ volatile ("nop");
        }
        GPIOB->ODR ^= (1u << 13);
    }
}
