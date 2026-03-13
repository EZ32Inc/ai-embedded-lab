#include <stdint.h>

#define RCC_BASE 0x40021000
#define RCC_APB2ENR (*(volatile uint32_t *)(RCC_BASE + 0x18))

#define GPIOA_BASE 0x40010800
#define GPIOA_CRL (*(volatile uint32_t *)(GPIOA_BASE + 0x00))
#define GPIOA_CRH (*(volatile uint32_t *)(GPIOA_BASE + 0x04))
#define GPIOA_IDR (*(volatile uint32_t *)(GPIOA_BASE + 0x08))
#define GPIOA_ODR (*(volatile uint32_t *)(GPIOA_BASE + 0x0C))

#define GPIOB_BASE 0x40010C00
#define GPIOB_CRH (*(volatile uint32_t *)(GPIOB_BASE + 0x04))
#define GPIOB_IDR (*(volatile uint32_t *)(GPIOB_BASE + 0x08))

#define GPIOC_BASE 0x40011000
#define GPIOC_CRH (*(volatile uint32_t *)(GPIOC_BASE + 0x04))
#define GPIOC_ODR (*(volatile uint32_t *)(GPIOC_BASE + 0x0C))

#define SYSTICK_BASE 0xE000E010u
#define SYST_CSR (*(volatile uint32_t *)(SYSTICK_BASE + 0x00u))
#define SYST_RVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x04u))
#define SYST_CVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x08u))

#define RCC_IOPAEN (1u << 2)
#define RCC_IOPBEN (1u << 3)
#define RCC_IOPCEN (1u << 4)

#define SYST_CSR_ENABLE (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

int main(void) {
    RCC_APB2ENR |= (RCC_IOPAEN | RCC_IOPBEN | RCC_IOPCEN);

    /* PA4 = external machine-checkable status output. */
    GPIOA_CRL &= ~(0xFu << 16);
    GPIOA_CRL |= (0x3u << 16);

    /* PA8 = GPIO loopback source. */
    GPIOA_CRH &= ~(0xFu << 0);
    GPIOA_CRH |= (0x3u << 0);

    /* PB8 = sampled loopback input. */
    GPIOB_CRH &= ~(0xFu << 0);
    GPIOB_CRH |= (0x4u << 0);

    /* PC13 = status LED. */
    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x2u << 20);
    GPIOC_ODR |= (1u << 13);

    SYST_RVR = 7999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    uint32_t drive_phase_ms = 0u;
    uint32_t status_phase_ms = 0u;
    uint32_t led_ms = 0u;
    uint32_t sense_window_ms = 0u;
    uint8_t drive_high = 0u;
    uint8_t status_high = 0u;
    uint8_t saw_high = 0u;
    uint8_t saw_low = 0u;
    uint8_t gpio_good = 0u;

    while (1) {
        if ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {
            continue;
        }

        drive_phase_ms += 1u;
        status_phase_ms += 1u;
        led_ms += 1u;
        sense_window_ms += 1u;

        if (drive_phase_ms >= 5u) {
            drive_phase_ms = 0u;
            drive_high ^= 1u;
            if (drive_high != 0u) {
                GPIOA_ODR |= (1u << 8);
            } else {
                GPIOA_ODR &= ~(1u << 8);
            }
        }

        if ((GPIOB_IDR & (1u << 8)) != 0u) {
            saw_high = 1u;
        } else {
            saw_low = 1u;
        }

        if (sense_window_ms >= 100u) {
            gpio_good = (uint8_t)(saw_high != 0u && saw_low != 0u);
            saw_high = 0u;
            saw_low = 0u;
            sense_window_ms = 0u;
        }

        if (status_phase_ms >= 5u) {
            status_phase_ms = 0u;
            status_high ^= 1u;
            if (gpio_good != 0u && status_high != 0u) {
                GPIOA_ODR |= (1u << 4);
            } else {
                GPIOA_ODR &= ~(1u << 4);
            }
        }

        if (led_ms >= (gpio_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOC_ODR ^= (1u << 13);
        }
    }
}
