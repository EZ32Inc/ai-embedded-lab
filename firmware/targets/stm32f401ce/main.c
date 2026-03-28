#include "stm32f4xx.h"

#define AEL_SIG_PORT   GPIOA
#define AEL_SIG_PIN    2u
#define AEL_LED_PORT   GPIOC
#define AEL_LED_PIN    13u
#define AEL_RCC_GPIOEN (RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOCEN)

void __libc_init_array(void) {}

static void gpio_set_output(GPIO_TypeDef *gpio, uint32_t pin) {
    const uint32_t shift = pin * 2u;
    gpio->MODER &= ~(0x3u << shift);
    gpio->MODER |= (0x1u << shift);
    gpio->OTYPER &= ~(1u << pin);
    gpio->OSPEEDR |= (0x3u << shift);
    gpio->PUPDR &= ~(0x3u << shift);
}

static void systick_init_1khz(void) {
    SysTick->LOAD = 16000u - 1u;
    SysTick->VAL = 0u;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk;
}

int main(void) {
    RCC->AHB1ENR |= AEL_RCC_GPIOEN;
    (void)RCC->AHB1ENR;

    gpio_set_output(AEL_SIG_PORT, AEL_SIG_PIN);
    gpio_set_output(AEL_LED_PORT, AEL_LED_PIN);
    systick_init_1khz();

    uint32_t sig_ms = 0;
    uint32_t led_ms = 0;

    while (1) {
        if ((SysTick->CTRL & SysTick_CTRL_COUNTFLAG_Msk) == 0u) {
            continue;
        }

        if (++sig_ms >= 5u) {
            sig_ms = 0u;
            AEL_SIG_PORT->ODR ^= (1u << AEL_SIG_PIN);
        }
        if (++led_ms >= 250u) {
            led_ms = 0u;
            AEL_LED_PORT->ODR ^= (1u << AEL_LED_PIN);
        }
    }
}
