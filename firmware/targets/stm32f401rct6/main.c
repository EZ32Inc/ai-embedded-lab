#include <stdint.h>

#define RCC_BASE    0x40023800u
#define RCC_AHB1ENR (*(volatile uint32_t *)(RCC_BASE + 0x30u))

#define GPIOA_BASE  0x40020000u
#define GPIOA_MODER (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_ODR   (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))

#define GPIOC_BASE  0x40020800u
#define GPIOC_MODER (*(volatile uint32_t *)(GPIOC_BASE + 0x00u))
#define GPIOC_ODR   (*(volatile uint32_t *)(GPIOC_BASE + 0x14u))

#define SYSTICK_BASE 0xE000E010u
#define SYST_CSR (*(volatile uint32_t *)(SYSTICK_BASE + 0x00u))
#define SYST_RVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x04u))
#define SYST_CVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x08u))

#define RCC_GPIOAEN      (1u << 0)
#define RCC_GPIOCEN      (1u << 2)
#define SYST_CSR_ENABLE     (1u << 0)
#define SYST_CSR_CLKSOURCE  (1u << 2)
#define SYST_CSR_COUNTFLAG  (1u << 16)

static inline void gpio_set_output(volatile uint32_t *moder, uint32_t pin) {
    const uint32_t shift = pin * 2u;
    *moder &= ~(0x3u << shift);
    *moder |= (0x1u << shift);
}

int main(void) {
    RCC_AHB1ENR |= (RCC_GPIOAEN | RCC_GPIOCEN);

    /* PA2 = fast square wave, PA3 = half rate — instrument captures both */
    gpio_set_output(&GPIOA_MODER, 2u);
    gpio_set_output(&GPIOA_MODER, 3u);
    gpio_set_output(&GPIOC_MODER, 13u);

    /* SysTick at 1 kHz from 16 MHz HSI */
    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    uint32_t tick = 0u;
    uint32_t div_pa2 = 0u;
    uint32_t div_pa3 = 0u;
    uint32_t led_ms  = 0u;

    while (1) {
        if ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {
            continue;
        }
        tick++;

        /* PA2: toggle every 20 ms → 25 Hz */
        if (++div_pa2 >= 20u) {
            div_pa2 = 0u;
            GPIOA_ODR ^= (1u << 2);
        }
        /* PA3: toggle every 40 ms → 12.5 Hz (half of PA2) */
        if (++div_pa3 >= 40u) {
            div_pa3 = 0u;
            GPIOA_ODR ^= (1u << 3);
        }
        /* PC13: LED blink 500 ms */
        if (++led_ms >= 500u) {
            led_ms = 0u;
            GPIOC_ODR ^= (1u << 13);
        }
        (void)tick;
    }
}
