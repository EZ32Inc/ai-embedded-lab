/* stm32f407vg — AEL draft firmware template (Group: stm32 / subgroup: stm32f4)
 *
 * Cortex-M4 with FPU — pre-filled for STM32F4xx family.
 *
 * PLACEHOLDER: set the exact MCU variant define in Makefile (e.g. STM32F407xx, STM32F401xE)
 * PLACEHOLDER: update GPIO port/pin assignments below for your board
 */
#include "stm32f4xx.h"

/* PLACEHOLDER: update with your board's GPIO configuration */
#define AEL_SIG_PORT   GPIOA                  /* PLACEHOLDER: signature output port */
#define AEL_SIG_PIN    2u                     /* PLACEHOLDER: signature output pin */
#define AEL_LED_PORT   GPIOC                  /* PLACEHOLDER: LED port */
#define AEL_LED_PIN    13u                    /* PLACEHOLDER: LED pin */
#define AEL_RCC_GPIOEN (RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOCEN)  /* PLACEHOLDER: enable clocks for your ports */

void __libc_init_array(void) {}

static void gpio_set_output(GPIO_TypeDef *gpio, uint32_t pin) {
    const uint32_t shift = pin * 2u;
    gpio->MODER &= ~(0x3u << shift);
    gpio->MODER |= (0x1u << shift);
    gpio->OTYPER &= ~(1u << pin);
    gpio->OSPEEDR |= (0x3u << shift);
    gpio->PUPDR &= ~(0x3u << shift);
}

int main(void) {
    RCC->AHB1ENR |= AEL_RCC_GPIOEN;
    (void)RCC->AHB1ENR;

    gpio_set_output(AEL_SIG_PORT, AEL_SIG_PIN);
    gpio_set_output(AEL_LED_PORT, AEL_LED_PIN);

    uint32_t div_sig = 0;
    uint32_t div_led = 0;

    while (1) {
        if (++div_sig >= 200u) {
            div_sig = 0;
            AEL_SIG_PORT->ODR ^= (1u << AEL_SIG_PIN);
        }
        if (++div_led >= 1500000u) {
            div_led = 0;
            AEL_LED_PORT->ODR ^= (1u << AEL_LED_PIN);
        }
    }
}
