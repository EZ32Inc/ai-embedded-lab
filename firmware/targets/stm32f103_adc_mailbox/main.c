#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x20004C00u
#include "../ael_mailbox.h"

#define RCC_BASE 0x40021000
#define RCC_APB2ENR (*(volatile uint32_t *)(RCC_BASE + 0x18))

#define GPIOA_BASE 0x40010800
#define GPIOA_CRL (*(volatile uint32_t *)(GPIOA_BASE + 0x00))
#define GPIOA_CRH (*(volatile uint32_t *)(GPIOA_BASE + 0x04))
#define GPIOA_ODR (*(volatile uint32_t *)(GPIOA_BASE + 0x0C))

#define GPIOC_BASE 0x40011000
#define GPIOC_CRH (*(volatile uint32_t *)(GPIOC_BASE + 0x04))
#define GPIOC_ODR (*(volatile uint32_t *)(GPIOC_BASE + 0x0C))

#define USART1_BASE 0x40013800
#define USART1_SR (*(volatile uint32_t *)(USART1_BASE + 0x00))
#define USART1_DR (*(volatile uint32_t *)(USART1_BASE + 0x04))
#define USART1_BRR (*(volatile uint32_t *)(USART1_BASE + 0x08))
#define USART1_CR1 (*(volatile uint32_t *)(USART1_BASE + 0x0C))

#define ADC1_BASE 0x40012400
#define ADC1_SR (*(volatile uint32_t *)(ADC1_BASE + 0x00))
#define ADC1_CR1 (*(volatile uint32_t *)(ADC1_BASE + 0x04))
#define ADC1_CR2 (*(volatile uint32_t *)(ADC1_BASE + 0x08))
#define ADC1_SMPR2 (*(volatile uint32_t *)(ADC1_BASE + 0x10))
#define ADC1_SQR3 (*(volatile uint32_t *)(ADC1_BASE + 0x34))
#define ADC1_DR (*(volatile uint32_t *)(ADC1_BASE + 0x4C))

#define SYSTICK_BASE 0xE000E010u
#define SYST_CSR (*(volatile uint32_t *)(SYSTICK_BASE + 0x00u))
#define SYST_RVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x04u))
#define SYST_CVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x08u))

#define RCC_IOPAEN (1u << 2)
#define RCC_IOPCEN (1u << 4)
#define RCC_ADC1EN (1u << 9)
#define ADC_CR2_ADON (1u << 0)
#define ADC_CR2_CAL (1u << 2)
#define ADC_CR2_RSTCAL (1u << 3)
#define ADC_CR2_SWSTART (1u << 22)
#define ADC_CR2_EXTTRIG (1u << 20)
#define ADC_CR2_EXTSEL_SWSTART (0x7u << 17)
#define ADC_SR_EOC (1u << 1)
#define SYST_CSR_ENABLE (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

static void adc1_init(void) {
    GPIOA_CRL &= ~(0xFu << 0);
    ADC1_SMPR2 |= (0x7u << 0);
    ADC1_CR1 = 0u;
    ADC1_SQR3 = 0u;
    ADC1_CR2 = ADC_CR2_ADON;
    for (volatile uint32_t i = 0; i < 10000u; ++i) {
    }
    ADC1_CR2 |= ADC_CR2_RSTCAL;
    while ((ADC1_CR2 & ADC_CR2_RSTCAL) != 0u) {
    }
    ADC1_CR2 |= ADC_CR2_CAL;
    while ((ADC1_CR2 & ADC_CR2_CAL) != 0u) {
    }
}

static uint8_t adc1_read(uint16_t *out) {
    ADC1_SR = 0u;
    ADC1_CR2 |= ADC_CR2_ADON;
    ADC1_CR2 &= ~(0x7u << 17);
    ADC1_CR2 |= ADC_CR2_EXTSEL_SWSTART;
    ADC1_CR2 |= ADC_CR2_EXTTRIG | ADC_CR2_SWSTART;
    for (uint32_t i = 0; i < 100000u; ++i) {
        if ((ADC1_SR & ADC_SR_EOC) != 0u) {
            *out = (uint16_t)(ADC1_DR & 0xFFFFu);
            return 1u;
        }
    }
    return 0u;
}

int main(void) {
    RCC_APB2ENR |= (RCC_IOPAEN | RCC_IOPCEN | RCC_ADC1EN);

    // PA1 is the loopback source and PA4..PA7 are the existing GPIO signature pins.
    GPIOA_CRL &= ~((0xFu << 4) | (0xFFFFu << 16));
    GPIOA_CRL |= (0x3u << 4) | (0x3333u << 16);
    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x2u << 20);
    GPIOC_ODR |= (1u << 13);

    adc1_init();
    ael_mailbox_init();

    SYST_RVR = 7999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    uint32_t phase_ms = 0;
    uint32_t pa5_ms = 0;
    uint32_t pa6_ms = 0;
    uint32_t pa7_ms = 0;
    uint32_t led_ms = 0;
    uint8_t phase_high = 0u;
    uint8_t adc_good = 0u;
    uint32_t success_count = 0u;
    uint32_t failure_count = 0u;
    while (1) {
        if ((SYST_CSR & SYST_CSR_COUNTFLAG) != 0u) {
            phase_ms += 1u;
            led_ms += 1u;
            pa5_ms += 1u;
            pa6_ms += 1u;
            pa7_ms += 1u;
        }

        // Bounded ADC loopback proof:
        // - drive PA1 low/high in 5 ms half-phases (~100 Hz square wave)
        // - sample PA0/ADC1_IN0 once per phase
        // - mirror the validated ADC result onto PA4
        // If the ADC sample does not match the expected state, force PA4 low.
        if (phase_ms >= 5u) {
            phase_ms = 0u;
            phase_high ^= 1u;
            if (phase_high != 0u) {
                GPIOA_ODR |= (1u << 1);
            } else {
                GPIOA_ODR &= ~(1u << 1);
            }

            uint16_t value = 0u;
            uint8_t ok = adc1_read(&value);
            if (phase_high != 0u) {
                adc_good = (uint8_t)(ok != 0u && value > 3000u);
            } else {
                adc_good = (uint8_t)(ok != 0u && value < 1000u);
            }
            if (adc_good != 0u) {
                success_count += 1u;
                failure_count = 0u;
                if (success_count >= 4u && AEL_MAILBOX->status != AEL_STATUS_PASS) {
                    ael_mailbox_pass();
                }
            } else {
                failure_count += 1u;
                if (failure_count >= 4u && AEL_MAILBOX->status != AEL_STATUS_PASS) {
                    ael_mailbox_fail(0xAD01u, value);
                    while (1) {
                    }
                }
            }

            if (adc_good != 0u && phase_high != 0u) {
                GPIOA_ODR |= (1u << 4);
            } else if (phase_high == 0u) {
                GPIOA_ODR &= ~(1u << 4);
            } else {
                GPIOA_ODR &= ~(1u << 4);
            }
        }

        if (pa5_ms >= 2u) {
            pa5_ms = 0u;
            GPIOA_ODR ^= (1u << 5);
        }
        if (pa6_ms >= 3u) {
            pa6_ms = 0u;
            GPIOA_ODR ^= (1u << 6);
        }
        if (pa7_ms >= 4u) {
            pa7_ms = 0u;
            GPIOA_ODR ^= (1u << 7);
        }

        uint32_t led_period_ms = adc_good ? 500u : 250u;
        if (led_ms >= led_period_ms) {
            led_ms = 0u;
            GPIOC_ODR ^= (1u << 13);
        }
        if (AEL_MAILBOX->status == AEL_STATUS_PASS) {
            AEL_MAILBOX->detail0 += 1u;
        }
    }
}
