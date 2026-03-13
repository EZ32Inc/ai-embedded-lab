#include <stdint.h>

#define RCC_BASE 0x40021000
#define RCC_APB2ENR (*(volatile uint32_t *)(RCC_BASE + 0x18))
#define RCC_APB1ENR (*(volatile uint32_t *)(RCC_BASE + 0x1C))

#define GPIOA_BASE 0x40010800
#define GPIOA_CRL (*(volatile uint32_t *)(GPIOA_BASE + 0x00))
#define GPIOA_CRH (*(volatile uint32_t *)(GPIOA_BASE + 0x04))
#define GPIOA_ODR (*(volatile uint32_t *)(GPIOA_BASE + 0x0C))

#define GPIOB_BASE 0x40010C00
#define GPIOB_CRH (*(volatile uint32_t *)(GPIOB_BASE + 0x04))

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

#define TIM4_BASE 0x40000800
#define TIM4_CR1 (*(volatile uint32_t *)(TIM4_BASE + 0x00))
#define TIM4_DIER (*(volatile uint32_t *)(TIM4_BASE + 0x0C))
#define TIM4_SR (*(volatile uint32_t *)(TIM4_BASE + 0x10))
#define TIM4_EGR (*(volatile uint32_t *)(TIM4_BASE + 0x14))
#define TIM4_CCMR2 (*(volatile uint32_t *)(TIM4_BASE + 0x1C))
#define TIM4_CCER (*(volatile uint32_t *)(TIM4_BASE + 0x20))
#define TIM4_CNT (*(volatile uint32_t *)(TIM4_BASE + 0x24))
#define TIM4_PSC (*(volatile uint32_t *)(TIM4_BASE + 0x28))
#define TIM4_ARR (*(volatile uint32_t *)(TIM4_BASE + 0x2C))
#define TIM4_CCR3 (*(volatile uint32_t *)(TIM4_BASE + 0x3C))

#define SYSTICK_BASE 0xE000E010u
#define SYST_CSR (*(volatile uint32_t *)(SYSTICK_BASE + 0x00u))
#define SYST_RVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x04u))
#define SYST_CVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x08u))

#define RCC_IOPAEN (1u << 2)
#define RCC_IOPBEN (1u << 3)
#define RCC_IOPCEN (1u << 4)
#define RCC_AFIOEN (1u << 0)
#define RCC_TIM1EN (1u << 11)
#define RCC_TIM4EN (1u << 2)

#define TIM_CR1_CEN (1u << 0)
#define TIM_CR1_ARPE (1u << 7)
#define TIM_CCER_CC1E (1u << 0)
#define TIM_CCER_CC3E (1u << 8)
#define TIM_BDTR_MOE (1u << 15)
#define TIM_SR_CC3IF (1u << 3)

#define SYST_CSR_ENABLE (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

static void tim1_pwm_init(void) {
    /* PA8 = TIM1_CH1 alternate-function push-pull 50 MHz. */
    GPIOA_CRH &= ~(0xFu << 0);
    GPIOA_CRH |= (0xBu << 0);

    /* 8 MHz / (7999 + 1) = 1 kHz timer tick. ARR=19 -> 50 Hz PWM, CCR1=10 -> 50% duty. */
    TIM1_PSC = 7999u;
    TIM1_ARR = 19u;
    TIM1_CCR1 = 10u;
    TIM1_CCMR1 = (6u << 4) | (1u << 3);
    TIM1_CCER = TIM_CCER_CC1E;
    TIM1_EGR = 1u;
    TIM1_BDTR = TIM_BDTR_MOE;
    TIM1_CR1 = TIM_CR1_ARPE | TIM_CR1_CEN;
}

static void tim4_capture_init(void) {
    /* PB8 = TIM4_CH3 input floating. */
    GPIOB_CRH &= ~(0xFu << 0);
    GPIOB_CRH |= (0x4u << 0);

    /* 8 MHz / (799 + 1) = 10 kHz timer tick. 50 Hz source -> ~200 ticks between rising edges. */
    TIM4_PSC = 799u;
    TIM4_ARR = 0xFFFFu;
    TIM4_CNT = 0u;
    TIM4_CCMR2 = 0x1u; /* CC3 mapped to TI3 input. */
    TIM4_CCER = TIM_CCER_CC3E; /* rising edge capture */
    TIM4_EGR = 1u;
    TIM4_SR = 0u;
    TIM4_CR1 = TIM_CR1_CEN;
}

int main(void) {
    RCC_APB2ENR |= (RCC_AFIOEN | RCC_IOPAEN | RCC_IOPBEN | RCC_IOPCEN | RCC_TIM1EN);
    RCC_APB1ENR |= RCC_TIM4EN;

    /* PA4 = external machine-checkable status output. */
    GPIOA_CRL &= ~(0xFu << 16);
    GPIOA_CRL |= (0x3u << 16);

    /* PC13 = status LED. */
    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x2u << 20);
    GPIOC_ODR |= (1u << 13);

    tim1_pwm_init();
    tim4_capture_init();

    SYST_RVR = 7999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    uint32_t status_phase_ms = 0u;
    uint32_t led_ms = 0u;
    uint32_t window_ms = 0u;
    uint8_t status_high = 0u;
    uint8_t capture_good = 0u;
    uint8_t have_last = 0u;
    uint16_t last_capture = 0u;
    uint32_t capture_count = 0u;
    uint32_t good_periods = 0u;

    while (1) {
        if ((TIM4_SR & TIM_SR_CC3IF) != 0u) {
            uint16_t current = (uint16_t)TIM4_CCR3;
            TIM4_SR &= ~TIM_SR_CC3IF;
            if (have_last != 0u) {
                uint16_t delta = (uint16_t)(current - last_capture);
                if (delta >= 150u && delta <= 250u) {
                    good_periods += 1u;
                }
            } else {
                have_last = 1u;
            }
            last_capture = current;
            capture_count += 1u;
        }

        if ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {
            continue;
        }

        status_phase_ms += 1u;
        led_ms += 1u;
        window_ms += 1u;

        if (window_ms >= 100u) {
            capture_good = (uint8_t)(capture_count >= 3u && good_periods >= 2u);
            capture_count = 0u;
            good_periods = 0u;
            window_ms = 0u;
        }

        if (status_phase_ms >= 5u) {
            status_phase_ms = 0u;
            status_high ^= 1u;
            if (capture_good != 0u && status_high != 0u) {
                GPIOA_ODR |= (1u << 4);
            } else {
                GPIOA_ODR &= ~(1u << 4);
            }
        }

        if (led_ms >= (capture_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOC_ODR ^= (1u << 13);
        }
    }
}
