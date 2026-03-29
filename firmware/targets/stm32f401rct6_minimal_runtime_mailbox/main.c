#include <stdint.h>

#include "ael_mailbox.h"

#define RCC_BASE    0x40023800u
#define RCC_AHB1ENR (*(volatile uint32_t *)(RCC_BASE + 0x30u))

#define GPIOC_BASE  0x40020800u
#define GPIOC_MODER (*(volatile uint32_t *)(GPIOC_BASE + 0x00u))
#define GPIOC_ODR   (*(volatile uint32_t *)(GPIOC_BASE + 0x14u))

#define SYSTICK_BASE 0xE000E010u
#define SYST_CSR (*(volatile uint32_t *)(SYSTICK_BASE + 0x00u))
#define SYST_RVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x04u))
#define SYST_CVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x08u))

#define RCC_GPIOCEN         (1u << 2)
#define SYST_CSR_ENABLE     (1u << 0)
#define SYST_CSR_CLKSOURCE  (1u << 2)
#define SYST_CSR_COUNTFLAG  (1u << 16)

static inline void gpio_set_output(volatile uint32_t *moder, uint32_t pin) {
    const uint32_t shift = pin * 2u;
    *moder &= ~(0x3u << shift);
    *moder |= (0x1u << shift);
}

int main(void) {
    uint32_t settle_ms = 0u;
    uint32_t led_ms = 0u;
    uint32_t heartbeat = 0u;

    RCC_AHB1ENR |= RCC_GPIOCEN;
    gpio_set_output(&GPIOC_MODER, 13u);

    /* SysTick at 1 kHz from 16 MHz HSI. */
    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    ael_mailbox_init();

    while (1) {
        if ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {
            continue;
        }

        if (AEL_MAILBOX->status == AEL_STATUS_RUNNING) {
            if (++settle_ms >= 50u) {
                ael_mailbox_pass();
                heartbeat = 1u;
                AEL_MAILBOX->detail0 = heartbeat;
            }
            continue;
        }

        if (++led_ms >= 1000u) {
            led_ms = 0u;
            GPIOC_ODR ^= (1u << 13);
            heartbeat++;
            AEL_MAILBOX->detail0 = heartbeat;
        }
    }
}
