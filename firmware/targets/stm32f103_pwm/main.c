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

#define TIM1_BASE 0x40012C00
#define TIM1_CR1 (*(volatile uint32_t *)(TIM1_BASE + 0x00))
#define TIM1_EGR (*(volatile uint32_t *)(TIM1_BASE + 0x14))
#define TIM1_CCMR1 (*(volatile uint32_t *)(TIM1_BASE + 0x18))
#define TIM1_CCER (*(volatile uint32_t *)(TIM1_BASE + 0x20))
#define TIM1_PSC (*(volatile uint32_t *)(TIM1_BASE + 0x28))
#define TIM1_ARR (*(volatile uint32_t *)(TIM1_BASE + 0x2C))
#define TIM1_CCR1 (*(volatile uint32_t *)(TIM1_BASE + 0x34))
#define TIM1_BDTR (*(volatile uint32_t *)(TIM1_BASE + 0x44))

#define SYSTICK_BASE 0xE000E010u
#define SYST_CSR (*(volatile uint32_t *)(SYSTICK_BASE + 0x00u))
#define SYST_RVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x04u))
#define SYST_CVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x08u))

#define RCC_IOPAEN (1u << 2)
#define RCC_IOPBEN (1u << 3)
#define RCC_IOPCEN (1u << 4)
#define RCC_AFIOEN (1u << 0)
#define RCC_TIM1EN (1u << 11)

#define TIM_CR1_CEN (1u << 0)
#define TIM_CR1_ARPE (1u << 7)
#define TIM_CCER_CC1E (1u << 0)
#define TIM_BDTR_MOE (1u << 15)

#define SYST_CSR_ENABLE (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

static void tim1_pwm_init(void) {
    /* PA8 = TIM1_CH1 alternate-function push-pull 50 MHz. */
    GPIOA_CRH &= ~(0xFu << 0);
    GPIOA_CRH |= (0xBu << 0);

    /* PB8 = input floating, sampled internally by firmware through the loopback. */
    GPIOB_CRH &= ~(0xFu << 0);
    GPIOB_CRH |= (0x4u << 0);

    /* 8 MHz / (7999 + 1) = 1 kHz timer tick. ARR=19 -> 50 Hz PWM, CCR1=10 -> 50% duty. */
    TIM1_PSC = 7999u;
    TIM1_ARR = 19u;
    TIM1_CCR1 = 10u;
    TIM1_CCMR1 = (6u << 4) | (1u << 3); /* PWM mode 1, preload enable on CH1 */
    TIM1_CCER = TIM_CCER_CC1E;
    TIM1_EGR = 1u;
    TIM1_BDTR = TIM_BDTR_MOE;
    TIM1_CR1 = TIM_CR1_ARPE | TIM_CR1_CEN;
}

int main(void) {
    RCC_APB2ENR |= (RCC_AFIOEN | RCC_IOPAEN | RCC_IOPBEN | RCC_IOPCEN | RCC_TIM1EN);

    /* PA4 as external machine-checkable status output. */
    GPIOA_CRL &= ~(0xFu << 16);
    GPIOA_CRL |= (0x3u << 16);

    /* PC13 = status LED. */
    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x2u << 20);
    GPIOC_ODR |= (1u << 13);

    tim1_pwm_init();

    SYST_RVR = 7999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    uint32_t status_phase_ms = 0u;
    uint32_t led_ms = 0u;
    uint32_t sense_window_ms = 0u;
    uint8_t status_high = 0u;
    uint8_t saw_high = 0u;
    uint8_t saw_low = 0u;
    uint8_t pwm_good = 0u;

    while (1) {
        if ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {
            continue;
        }

        status_phase_ms += 1u;
        led_ms += 1u;
        sense_window_ms += 1u;

        if ((GPIOB_IDR & (1u << 8)) != 0u) {
            saw_high = 1u;
        } else {
            saw_low = 1u;
        }

        if (sense_window_ms >= 100u) {
            pwm_good = (uint8_t)(saw_high != 0u && saw_low != 0u);
            saw_high = 0u;
            saw_low = 0u;
            sense_window_ms = 0u;
        }

        if (status_phase_ms >= 5u) {
            status_phase_ms = 0u;
            status_high ^= 1u;
            if (pwm_good != 0u && status_high != 0u) {
                GPIOA_ODR |= (1u << 4);
            } else {
                GPIOA_ODR &= ~(1u << 4);
            }
        }

        if (led_ms >= (pwm_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOC_ODR ^= (1u << 13);
        }
    }
}
