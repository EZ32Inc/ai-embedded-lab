#include <stdint.h>

#define RCC_BASE 0x40023800u
#define RCC_AHB1ENR (*(volatile uint32_t *)(RCC_BASE + 0x30u))

#define GPIOA_BASE 0x40020000u
#define GPIOA_MODER (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_ODR (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))

#define GPIOC_BASE 0x40020800u
#define GPIOC_MODER (*(volatile uint32_t *)(GPIOC_BASE + 0x00u))
#define GPIOC_ODR (*(volatile uint32_t *)(GPIOC_BASE + 0x14u))

#define SYSTICK_BASE 0xE000E010u
#define SYST_CSR (*(volatile uint32_t *)(SYSTICK_BASE + 0x00u))
#define SYST_RVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x04u))
#define SYST_CVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x08u))

#define RCC_GPIOAEN (1u << 0)
#define RCC_GPIOCEN (1u << 2)
#define SYST_CSR_ENABLE (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

static inline void gpio_set_output(volatile uint32_t *moder, uint32_t pin) {
    const uint32_t shift = pin * 2u;
    *moder &= ~(0x3u << shift);
    *moder |= (0x1u << shift);
}

int main(void) {
    // Enable GPIOA and GPIOC on STM32F401.
    RCC_AHB1ENR |= (RCC_GPIOAEN | RCC_GPIOCEN);

    // Configure PA2, PA3, and PA4 as general purpose outputs.
    gpio_set_output(&GPIOA_MODER, 2u);
    gpio_set_output(&GPIOA_MODER, 3u);
    gpio_set_output(&GPIOA_MODER, 4u);

    // Configure PC13 for the board LED.
    gpio_set_output(&GPIOC_MODER, 13u);

    // Run SysTick at 1 kHz from the default 16 MHz HSI core clock.
    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    uint32_t div0 = 0;
    uint32_t div1 = 0;
    uint32_t div2 = 0;
    uint32_t led_ms = 0;
    while (1) {
        if (++div0 >= 200u) {
            div0 = 0;
            GPIOA_ODR ^= (1u << 4);
        }
        if (++div1 >= 400u) {
            div1 = 0;
            GPIOA_ODR ^= (1u << 3);
        }
        if (++div2 >= 600u) {
            div2 = 0;
            GPIOA_ODR ^= (1u << 2);
        }

        if ((SYST_CSR & SYST_CSR_COUNTFLAG) != 0u) {
            led_ms += 1u;
        }
        if (led_ms >= 500u) {
            led_ms = 0u;
            GPIOC_ODR ^= (1u << 13);
        }
    }
}
