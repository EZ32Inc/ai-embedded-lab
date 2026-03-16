#include <stdint.h>
#include "../ael_mailbox.h"

/* STM32G431 — GPIO on AHB2 */
#define RCC_BASE       0x40021000u
#define RCC_AHB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x4Cu))
#define RCC_APB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x60u))

#define GPIOA_BASE     0x48000000u
#define GPIOA_MODER    (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_OTYPER   (*(volatile uint32_t *)(GPIOA_BASE + 0x04u))
#define GPIOA_OSPEEDR  (*(volatile uint32_t *)(GPIOA_BASE + 0x08u))
#define GPIOA_PUPDR    (*(volatile uint32_t *)(GPIOA_BASE + 0x0Cu))
#define GPIOA_IDR      (*(volatile uint32_t *)(GPIOA_BASE + 0x10u))
#define GPIOA_ODR      (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))
#define GPIOA_AFRH     (*(volatile uint32_t *)(GPIOA_BASE + 0x24u))

/* TIM1 (APB2) — PA8 CH1 AF6 on G431 */
#define TIM1_BASE      0x40012C00u
#define TIM1_CR1       (*(volatile uint32_t *)(TIM1_BASE + 0x00u))
#define TIM1_CCMR1     (*(volatile uint32_t *)(TIM1_BASE + 0x18u))
#define TIM1_CCER      (*(volatile uint32_t *)(TIM1_BASE + 0x20u))
#define TIM1_PSC       (*(volatile uint32_t *)(TIM1_BASE + 0x28u))
#define TIM1_ARR       (*(volatile uint32_t *)(TIM1_BASE + 0x2Cu))
#define TIM1_CCR1      (*(volatile uint32_t *)(TIM1_BASE + 0x34u))
#define TIM1_BDTR      (*(volatile uint32_t *)(TIM1_BASE + 0x44u))
#define TIM1_EGR       (*(volatile uint32_t *)(TIM1_BASE + 0x14u))

/* SysTick */
#define SYST_CSR       (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR       (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR       (*(volatile uint32_t *)0xE000E018u)

static void gpioa_set_output(uint32_t pin)
{
    const uint32_t sh = pin * 2u;
    GPIOA_MODER &= ~(0x3u << sh);
    GPIOA_MODER |=  (0x1u << sh);
    GPIOA_OTYPER &= ~(1u << pin);
    GPIOA_OSPEEDR |= (0x3u << sh);
}

static void gpioa_set_input(uint32_t pin)
{
    const uint32_t sh = pin * 2u;
    GPIOA_MODER &= ~(0x3u << sh);
    GPIOA_PUPDR &= ~(0x3u << sh);
}

static void tim1_pwm_init(void)
{
    /* PA8 = TIM1_CH1, AF6 on G431 */
    const uint32_t sh   = 8u * 2u;
    const uint32_t afsh = (8u - 8u) * 4u;
    GPIOA_MODER &= ~(0x3u << sh);
    GPIOA_MODER |=  (0x2u << sh);
    GPIOA_OTYPER &= ~(1u << 8);
    GPIOA_OSPEEDR |= (0x3u << sh);
    GPIOA_PUPDR &= ~(0x3u << sh);
    GPIOA_AFRH &= ~(0xFu << afsh);
    GPIOA_AFRH |=  (6u   << afsh);   /* AF6 = TIM1_CH1 on G431 */

    /* PSC=16000-1, ARR=20-1 → 50Hz, CCR1=10 → 50% duty */
    TIM1_PSC  = 16000u - 1u;
    TIM1_ARR  = 20u - 1u;
    TIM1_CCR1 = 10u;
    /* OC1M=110 (PWM mode 1), OC1PE=1 */
    TIM1_CCMR1 = (1u << 3) | (1u << 6) | (1u << 5);
    TIM1_CCER  = (1u << 0);   /* CC1E */
    TIM1_BDTR  = (1u << 15);  /* MOE */
    TIM1_EGR   = (1u << 0);   /* UG */
    TIM1_CR1   = (1u << 7) | (1u << 0);  /* ARPE, CEN */
}

int main(void)
{
    uint32_t sense_ms  = 0u;
    uint32_t status_ms = 0u;
    uint8_t status_high = 0u;
    uint8_t saw_high    = 0u;
    uint8_t saw_low     = 0u;
    uint8_t pwm_good    = 0u;
    uint8_t mb_settled  = 0u;

    RCC_AHB2ENR |= (1u << 0);   /* GPIOAEN */
    RCC_APB2ENR |= (1u << 11);  /* TIM1EN */
    (void)RCC_APB2ENR;

    gpioa_set_output(2u);  /* PA2: signal */
    gpioa_set_input(6u);   /* PA6: PWM sense (loopback from PA8) */
    tim1_pwm_init();       /* PA8: TIM1_CH1 50Hz 50% duty */

    GPIOA_ODR &= ~(1u << 2);

    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = (1u << 2) | (1u << 0);
    ael_mailbox_init();

    while (1) {
        if ((SYST_CSR & (1u << 16)) == 0u) { continue; }

        sense_ms  += 1u;
        status_ms += 1u;

        /* Sample PA6 (receives TIM1 PWM via PA8→PA6 loopback) */
        if ((GPIOA_IDR & (1u << 6)) != 0u) {
            saw_high = 1u;
        } else {
            saw_low = 1u;
        }

        /* Over 100ms window: expect both high and low seen */
        if (sense_ms >= 100u) {
            pwm_good = (uint8_t)(saw_high != 0u && saw_low != 0u);
            saw_high = 0u;
            saw_low  = 0u;
            sense_ms = 0u;
            if (mb_settled == 0u) {
                if (pwm_good != 0u) { ael_mailbox_pass(); }
                else { ael_mailbox_fail(0xE001u, 0u); }
                mb_settled = 1u;
            }
        }

        if (status_ms >= 5u) {
            status_ms = 0u;
            status_high ^= 1u;
            if (pwm_good != 0u && status_high != 0u) {
                GPIOA_ODR |= (1u << 2);
            } else {
                GPIOA_ODR &= ~(1u << 2);
            }
        }

        /* PA8 is TIM1 output — LED follows PWM, no separate toggle */
    }
}
