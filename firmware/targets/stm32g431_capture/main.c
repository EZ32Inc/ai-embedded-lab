#include <stdint.h>
#include "../ael_mailbox.h"

/* STM32G431 — GPIO on AHB2 */
#define RCC_BASE       0x40021000u
#define RCC_AHB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x4Cu))
#define RCC_APB1ENR1   (*(volatile uint32_t *)(RCC_BASE + 0x58u))
#define RCC_APB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x60u))

#define GPIOA_BASE     0x48000000u
#define GPIOA_MODER    (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_OTYPER   (*(volatile uint32_t *)(GPIOA_BASE + 0x04u))
#define GPIOA_OSPEEDR  (*(volatile uint32_t *)(GPIOA_BASE + 0x08u))
#define GPIOA_PUPDR    (*(volatile uint32_t *)(GPIOA_BASE + 0x0Cu))
#define GPIOA_ODR      (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))
#define GPIOA_AFRL     (*(volatile uint32_t *)(GPIOA_BASE + 0x20u))
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

/* TIM3 (APB1) — PA6 CH1 AF2 */
#define TIM3_BASE      0x40000400u
#define TIM3_CR1       (*(volatile uint32_t *)(TIM3_BASE + 0x00u))
#define TIM3_CCMR1     (*(volatile uint32_t *)(TIM3_BASE + 0x18u))
#define TIM3_CCER      (*(volatile uint32_t *)(TIM3_BASE + 0x20u))
#define TIM3_PSC       (*(volatile uint32_t *)(TIM3_BASE + 0x28u))
#define TIM3_ARR       (*(volatile uint32_t *)(TIM3_BASE + 0x2Cu))
#define TIM3_CCR1      (*(volatile uint32_t *)(TIM3_BASE + 0x34u))
#define TIM3_CNT       (*(volatile uint32_t *)(TIM3_BASE + 0x24u))
#define TIM3_SR        (*(volatile uint32_t *)(TIM3_BASE + 0x10u))
#define TIM3_EGR       (*(volatile uint32_t *)(TIM3_BASE + 0x14u))

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

static void gpioa_set_af_lo(uint32_t pin, uint32_t af)  /* pins 0-7 */
{
    const uint32_t sh   = pin * 2u;
    const uint32_t afsh = pin * 4u;
    GPIOA_MODER &= ~(0x3u << sh);
    GPIOA_MODER |=  (0x2u << sh);
    GPIOA_OTYPER &= ~(1u << pin);
    GPIOA_OSPEEDR |= (0x3u << sh);
    GPIOA_PUPDR &= ~(0x3u << sh);
    GPIOA_AFRL &= ~(0xFu << afsh);
    GPIOA_AFRL |=  (af   << afsh);
}

static void gpioa_set_af_hi(uint32_t pin, uint32_t af)  /* pins 8-15 */
{
    const uint32_t sh   = pin * 2u;
    const uint32_t afsh = (pin - 8u) * 4u;
    GPIOA_MODER &= ~(0x3u << sh);
    GPIOA_MODER |=  (0x2u << sh);
    GPIOA_OTYPER &= ~(1u << pin);
    GPIOA_OSPEEDR |= (0x3u << sh);
    GPIOA_PUPDR &= ~(0x3u << sh);
    GPIOA_AFRH &= ~(0xFu << afsh);
    GPIOA_AFRH |=  (af   << afsh);
}

static void tim1_source_init(void)
{
    /* PA8 = TIM1_CH1, AF6 on G431 */
    gpioa_set_af_hi(8u, 6u);

    /* PSC=16000-1 → timer clock = 1kHz, ARR=20-1 → 50Hz, CCR1=10 → 50% duty */
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

static void tim3_capture_init(void)
{
    /* PA6 = TIM3_CH1, AF2 */
    gpioa_set_af_lo(6u, 2u);

    /* PSC=1600-1 → timer clock = 10kHz, ARR=0xFFFF */
    TIM3_PSC   = 1600u - 1u;
    TIM3_ARR   = 0xFFFFu;
    TIM3_CNT   = 0u;
    /* CC1S=01 (input, TI1) */
    TIM3_CCMR1 = (1u << 0);
    TIM3_CCER  = (1u << 0);   /* CC1E */
    TIM3_EGR   = (1u << 0);   /* UG */
    TIM3_SR    = 0u;
    TIM3_CR1   = (1u << 0);   /* CEN */
}

int main(void)
{
    uint32_t status_ms    = 0u;
    uint32_t window_ms    = 0u;
    uint32_t led_ms       = 0u;
    uint8_t status_high   = 0u;
    uint8_t capture_good  = 0u;
    uint8_t have_last     = 0u;
    uint16_t last_capture = 0u;
    uint32_t capture_count = 0u;
    uint32_t good_periods  = 0u;
    uint8_t  mb_settled    = 0u;

    RCC_AHB2ENR  |= (1u << 0);   /* GPIOAEN */
    RCC_APB2ENR  |= (1u << 11);  /* TIM1EN */
    RCC_APB1ENR1 |= (1u << 1);   /* TIM3EN */
    (void)RCC_APB1ENR1;

    gpioa_set_output(2u);   /* PA2: signal */

    tim1_source_init();
    tim3_capture_init();

    GPIOA_ODR &= ~(1u << 2);

    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = (1u << 2) | (1u << 0);
    ael_mailbox_init();

    while (1) {
        /* Poll TIM3 CC1 capture flag */
        if ((TIM3_SR & (1u << 1)) != 0u) {
            const uint16_t current = (uint16_t)(TIM3_CCR1 & 0xFFFFu);
            TIM3_SR &= ~(1u << 1);   /* clear CC1IF */
            if (have_last != 0u) {
                const uint16_t delta = (uint16_t)(current - last_capture);
                /* 50Hz at 10kHz timer → period = 200 ticks; allow 150-250 */
                if (delta >= 150u && delta <= 250u) {
                    good_periods += 1u;
                }
            } else {
                have_last = 1u;
            }
            last_capture = current;
            capture_count += 1u;
        }

        if ((SYST_CSR & (1u << 16)) == 0u) { continue; }

        status_ms  += 1u;
        window_ms  += 1u;
        led_ms     += 1u;

        if (window_ms >= 100u) {
            capture_good  = (uint8_t)(capture_count >= 3u && good_periods >= 2u);
            capture_count = 0u;
            good_periods  = 0u;
            window_ms     = 0u;
            if (mb_settled == 0u) {
                if (capture_good != 0u) { ael_mailbox_pass(); }
                else { ael_mailbox_fail(0xE001u, 0u); }
                mb_settled = 1u;
            }
        }

        if (status_ms >= 5u) {
            status_ms = 0u;
            status_high ^= 1u;
            if (capture_good != 0u && status_high != 0u) {
                GPIOA_ODR |= (1u << 2);
            } else {
                GPIOA_ODR &= ~(1u << 2);
            }
        }

        /* PA8 is TIM1 output — no separate LED toggle */
        (void)led_ms;
    }
}
