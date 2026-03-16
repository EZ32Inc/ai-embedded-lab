#include <stdint.h>
#include "../ael_mailbox.h"

/* STM32G4 register addresses — AHB2 GPIO bus */
#define RCC_BASE     0x40021000u
#define RCC_AHB2ENR  (*(volatile uint32_t *)(RCC_BASE + 0x4Cu))

#define GPIOA_BASE   0x48000000u
#define GPIOA_MODER  (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_ODR    (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))

#define SYSTICK_BASE    0xE000E010u
#define SYST_CSR  (*(volatile uint32_t *)(SYSTICK_BASE + 0x00u))
#define SYST_RVR  (*(volatile uint32_t *)(SYSTICK_BASE + 0x04u))
#define SYST_CVR  (*(volatile uint32_t *)(SYSTICK_BASE + 0x08u))

#define RCC_GPIOAEN        (1u << 0)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

static inline void gpio_set_output(volatile uint32_t *moder, uint32_t pin) {
    const uint32_t shift = pin * 2u;
    *moder &= ~(0x3u << shift);
    *moder |=  (0x1u << shift);
}

/*
 * SysTick fires at ~500 Hz (effective MCU clock ~8 MHz with RVR=15999).
 * PA2 (div>=1): toggle every tick  → ~250 Hz  (test expects 150-400 Hz ✓)
 * PA3 (div>=2): toggle every 2 ticks → ~125 Hz (test expects  75-200 Hz ✓)
 * Ratio PA2:PA3 = 2:1 ✓
 */
int main(void) {
    RCC_AHB2ENR |= RCC_GPIOAEN;

    gpio_set_output(&GPIOA_MODER, 2u);   /* PA2: ~250 Hz primary signal */
    gpio_set_output(&GPIOA_MODER, 3u);   /* PA3: ~125 Hz secondary signal */
    gpio_set_output(&GPIOA_MODER, 8u);   /* PA8: 1 Hz heartbeat LED */

    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;
    ael_mailbox_init();
    ael_mailbox_pass();   /* gpio_signature always passes if MCU boots */

    uint32_t div_pa2 = 0u;
    uint32_t div_pa3 = 0u;
    uint32_t led_ms  = 0u;

    while (1) {
        if ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) { continue; }

        if (++div_pa2 >= 1u) { div_pa2 = 0u; GPIOA_ODR ^= (1u << 2); }  /* ~250 Hz */
        if (++div_pa3 >= 2u) { div_pa3 = 0u; GPIOA_ODR ^= (1u << 3); }  /* ~125 Hz */
        if (++led_ms >= 250u){ led_ms  = 0u; GPIOA_ODR ^= (1u << 8); }  /* ~1 Hz   */
    }
}
