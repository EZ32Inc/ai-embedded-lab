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
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOCEN;
    (void)RCC->AHB1ENR;

    gpio_set_output(GPIOA, 2u);
    gpio_set_output(GPIOA, 3u);
    gpio_set_output(GPIOC, 13u);

    uint32_t div0 = 0;
    uint32_t div1 = 0;
    uint32_t led_div = 0;

    while (1) {
        if (++div0 >= 200u) {
            div0 = 0;
            GPIOA->ODR ^= GPIO_ODR_OD2;
        }
        if (++div1 >= 400u) {
            div1 = 0;
            GPIOA->ODR ^= GPIO_ODR_OD3;
        }

        if (++led_div >= 1500000u) {
            led_div = 0u;
            GPIOC->ODR ^= GPIO_ODR_OD13;
        }
    }
}
