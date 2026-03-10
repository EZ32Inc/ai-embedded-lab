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

static void systick_init_1khz(void) {
    SystemCoreClockUpdate();
    SysTick_Config(SystemCoreClock / 1000u);
}

int main(void) {
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOCEN;
    (void)RCC->AHB1ENR;

    gpio_set_output(GPIOA, 2u);
    gpio_set_output(GPIOA, 3u);
    gpio_set_output(GPIOA, 4u);
    gpio_set_output(GPIOC, 13u);

    systick_init_1khz();

    uint32_t div0 = 0;
    uint32_t div1 = 0;
    uint32_t div2 = 0;
    uint32_t led_ms = 0;

    while (1) {
        if (++div0 >= 200u) {
            div0 = 0;
            GPIOA->ODR ^= GPIO_ODR_OD4;
        }
        if (++div1 >= 400u) {
            div1 = 0;
            GPIOA->ODR ^= GPIO_ODR_OD3;
        }
        if (++div2 >= 600u) {
            div2 = 0;
            GPIOA->ODR ^= GPIO_ODR_OD2;
        }
        if ((SysTick->CTRL & SysTick_CTRL_COUNTFLAG_Msk) != 0u) {
            led_ms += 1u;
        }
        if (led_ms >= 500u) {
            led_ms = 0u;
            GPIOC->ODR ^= GPIO_ODR_OD13;
        }
    }
}
