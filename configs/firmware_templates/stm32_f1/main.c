/* {SLUG} — AEL draft firmware template (Group: stm32 / subgroup: stm32f1)
 *
 * Cortex-M3 — pre-filled for STM32F1xx family.
 *
 * PLACEHOLDER: set the exact MCU variant define in Makefile (e.g. STM32F103xB, STM32F103xE)
 * PLACEHOLDER: update GPIO port/pin assignments below for your board
 *
 * NOTE: STM32F1 uses APB2 clock for GPIO (not AHB1 like F4).
 *       GPIO mode registers are also different (CRL/CRH, not MODER).
 */
#include "stm32f1xx.h"

/* PLACEHOLDER: update with your board's GPIO configuration */
#define AEL_SIG_PORT   GPIOA                  /* PLACEHOLDER: signature output port */
#define AEL_SIG_PIN    2u                     /* PLACEHOLDER: signature output pin */
#define AEL_LED_PORT   GPIOC                  /* PLACEHOLDER: LED port */
#define AEL_LED_PIN    13u                    /* PLACEHOLDER: LED pin (PC13 on blue-pill) */

void __libc_init_array(void) {}

/* STM32F1 GPIO output: use CRL (pins 0-7) or CRH (pins 8-15) */
static void gpio_set_output_2mhz_pp(GPIO_TypeDef *gpio, uint32_t pin) {
    if (pin < 8u) {
        uint32_t shift = pin * 4u;
        gpio->CRL &= ~(0xFu << shift);
        gpio->CRL |= (0x2u << shift);  /* Output 2MHz push-pull */
    } else {
        uint32_t shift = (pin - 8u) * 4u;
        gpio->CRH &= ~(0xFu << shift);
        gpio->CRH |= (0x2u << shift);
    }
}

int main(void) {
    /* Enable GPIOA and GPIOC clocks on APB2 */
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN | RCC_APB2ENR_IOPCEN;
    (void)RCC->APB2ENR;

    gpio_set_output_2mhz_pp(AEL_SIG_PORT, AEL_SIG_PIN);
    gpio_set_output_2mhz_pp(AEL_LED_PORT, AEL_LED_PIN);

    /* Active-low LED on blue-pill — start ON */
    AEL_LED_PORT->BRR = (1u << AEL_LED_PIN);

    uint32_t div_sig = 0;
    uint32_t div_led = 0;

    while (1) {
        if (++div_sig >= 200u) {
            div_sig = 0;
            AEL_SIG_PORT->ODR ^= (1u << AEL_SIG_PIN);
        }
        if (++div_led >= 600000u) {
            div_led = 0;
            AEL_LED_PORT->ODR ^= (1u << AEL_LED_PIN);
        }
    }
}
