/*
 * STM32F401RCT6 — TIM PWM + Input Capture Test
 *
 * PA8 → TIM1_CH1 (AF1): 1 kHz 50% duty PWM output.
 * PA6 → TIM3_CH1 (AF2): Input capture, measures PWM period.
 *
 * Timer clock: 16 MHz HSI / (PSC+1=16) = 1 MHz → 1 µs resolution.
 * TIM1: ARR=999, CCR1=500 → period=1000 µs, duty=50%.
 * TIM3: free-running 16-bit, captures rising edges on TI1.
 *
 * Accept period: 900–1100 µs (±10%).
 *
 * Mailbox at 0x2000FC00.
 *   PASS: period in range. detail0 = measured period (µs), then heartbeat.
 *   FAIL: error_code bit0=ERR_CAP_TIMEOUT, bit1=ERR_PERIOD.
 *         detail0 = measured period (µs), or 0 on timeout.
 *
 * Register addresses: RM0368 (STM32F401 Reference Manual).
 * Clock: 16 MHz HSI, no PLL, APBx prescaler = 1.
 */

#include <stdint.h>
#include "ael_mailbox.h"

/* ---- RCC ---------------------------------------------------------------- */
#define RCC_BASE        0x40023800u
#define RCC_AHB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x30u))
#define RCC_APB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x40u))
#define RCC_APB2ENR     (*(volatile uint32_t *)(RCC_BASE + 0x44u))
#define RCC_AHB1ENR_GPIOAEN (1u << 0)
#define RCC_APB1ENR_TIM3EN  (1u << 1)
#define RCC_APB2ENR_TIM1EN  (1u << 0)

/* ---- GPIOA -------------------------------------------------------------- */
#define GPIOA_BASE  0x40020000u
#define GPIOA_MODER (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_AFRL  (*(volatile uint32_t *)(GPIOA_BASE + 0x20u))
#define GPIOA_AFRH  (*(volatile uint32_t *)(GPIOA_BASE + 0x24u))

/* ---- TIM1 (APB2, advanced, base 0x40010000) ----------------------------- */
#define TIM1_BASE   0x40010000u
#define TIM1_CR1    (*(volatile uint32_t *)(TIM1_BASE + 0x00u))
#define TIM1_CCMR1  (*(volatile uint32_t *)(TIM1_BASE + 0x18u))
#define TIM1_CCER   (*(volatile uint32_t *)(TIM1_BASE + 0x20u))
#define TIM1_PSC    (*(volatile uint32_t *)(TIM1_BASE + 0x28u))
#define TIM1_ARR    (*(volatile uint32_t *)(TIM1_BASE + 0x2Cu))
#define TIM1_RCR    (*(volatile uint32_t *)(TIM1_BASE + 0x30u))
#define TIM1_CCR1   (*(volatile uint32_t *)(TIM1_BASE + 0x34u))
#define TIM1_BDTR   (*(volatile uint32_t *)(TIM1_BASE + 0x44u))
#define TIM1_CR1_CEN    (1u << 0)
#define TIM1_BDTR_MOE   (1u << 15)

/* ---- TIM3 (APB1, general-purpose, base 0x40000400) ---------------------- */
#define TIM3_BASE   0x40000400u
#define TIM3_CR1    (*(volatile uint32_t *)(TIM3_BASE + 0x00u))
#define TIM3_SR     (*(volatile uint32_t *)(TIM3_BASE + 0x10u))
#define TIM3_CCMR1  (*(volatile uint32_t *)(TIM3_BASE + 0x18u))
#define TIM3_CCER   (*(volatile uint32_t *)(TIM3_BASE + 0x20u))
#define TIM3_CNT    (*(volatile uint32_t *)(TIM3_BASE + 0x24u))
#define TIM3_PSC    (*(volatile uint32_t *)(TIM3_BASE + 0x28u))
#define TIM3_ARR    (*(volatile uint32_t *)(TIM3_BASE + 0x2Cu))
#define TIM3_CCR1   (*(volatile uint32_t *)(TIM3_BASE + 0x34u))
#define TIM3_SR_CC1IF (1u << 1)
#define TIM3_CR1_CEN  (1u << 0)

/* ---- SysTick ------------------------------------------------------------ */
#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

#define ERR_CAP_TIMEOUT (1u << 0)
#define ERR_PERIOD      (1u << 1)

#define CAP_TIMEOUT   2000000u   /* poll iterations */
#define PERIOD_MIN_US  900u
#define PERIOD_MAX_US 1100u

static void delay_ms(uint32_t ms)
{
    for (uint32_t i = 0u; i < ms; i++) {
        SYST_CVR = 0u;
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

int main(void)
{
    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    /* Enable clocks */
    RCC_AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    (void)RCC_AHB1ENR;
    RCC_APB1ENR |= RCC_APB1ENR_TIM3EN;
    (void)RCC_APB1ENR;
    RCC_APB2ENR |= RCC_APB2ENR_TIM1EN;
    (void)RCC_APB2ENR;

    /*
     * PA8 → AF1 (TIM1_CH1): MODER[17:16]=10, AFRH[3:0]=1
     * PA6 → AF2 (TIM3_CH1): MODER[13:12]=10, AFRL[27:24]=2
     */
    GPIOA_MODER &= ~(0x3u << 16u);
    GPIOA_MODER |=  (0x2u << 16u);
    GPIOA_AFRH  &= ~(0xFu <<  0u);
    GPIOA_AFRH  |=  (0x1u <<  0u);

    GPIOA_MODER &= ~(0x3u << 12u);
    GPIOA_MODER |=  (0x2u << 12u);
    GPIOA_AFRL  &= ~(0xFu << 24u);
    GPIOA_AFRL  |=  (0x2u << 24u);

    /*
     * TIM3: input capture on CH1 (TI1 = PA6), 1 MHz resolution.
     * CCMR1[1:0] = 01: IC1 mapped to TI1.
     * CCER bit 0: CC1E, bit 1: CC1P=0 (rising edge).
     * PSC=15 → 1 MHz. ARR=0xFFFF (free-running 16-bit).
     */
    TIM3_CR1   = 0u;
    TIM3_PSC   = 15u;
    TIM3_ARR   = 0xFFFFu;
    TIM3_CCMR1 = 0x1u;          /* CC1S=01: input on TI1 */
    TIM3_CCER  = (1u << 0u);    /* CC1E=1, CC1P=0 (rising) */
    TIM3_SR    = 0u;             /* clear flags */
    TIM3_CR1   = TIM3_CR1_CEN;

    /*
     * TIM1: PWM on CH1 (PA8), 1 kHz 50%, 1 MHz resolution.
     * CCMR1[6:4]=110 (PWM mode 1), CCMR1[3]=1 (OC1PE preload).
     * PSC=15, ARR=999, CCR1=500 → 1 kHz 50% duty.
     * BDTR[15]=1: MOE (main output enable, required for advanced timer).
     */
    TIM1_CR1   = 0u;
    TIM1_PSC   = 15u;
    TIM1_ARR   = 999u;
    TIM1_RCR   = 0u;
    TIM1_CCR1  = 500u;
    TIM1_CCMR1 = (0x6u << 4u) | (1u << 3u);  /* OC1M=110, OC1PE=1 */
    TIM1_CCER  = (1u << 0u);                  /* CC1E=1 */
    TIM1_BDTR  = TIM1_BDTR_MOE;
    TIM1_CR1   = TIM1_CR1_CEN;

    ael_mailbox_init();

    /* Wait for first rising-edge capture */
    uint32_t timeout = CAP_TIMEOUT;
    while ((TIM3_SR & TIM3_SR_CC1IF) == 0u) {
        if (--timeout == 0u) {
            ael_mailbox_fail(ERR_CAP_TIMEOUT, 0u);
            while (1) {}
        }
    }
    uint32_t t1 = TIM3_CCR1;   /* reading CCR1 clears CC1IF */

    /* Wait for second rising-edge capture */
    timeout = CAP_TIMEOUT;
    while ((TIM3_SR & TIM3_SR_CC1IF) == 0u) {
        if (--timeout == 0u) {
            ael_mailbox_fail(ERR_CAP_TIMEOUT, 0u);
            while (1) {}
        }
    }
    uint32_t t2 = TIM3_CCR1;

    /* Period in µs (1 MHz clock, 16-bit counter) */
    uint32_t period = (t2 - t1) & 0xFFFFu;

    if (period < PERIOD_MIN_US || period > PERIOD_MAX_US) {
        ael_mailbox_fail(ERR_PERIOD, period);
        while (1) {}
    }

    ael_mailbox_pass();
    AEL_MAILBOX->detail0 = period;   /* first read shows measured period */
    uint32_t iteration = 0u;
    while (1) {
        delay_ms(1u);
        AEL_MAILBOX->detail0 = ++iteration;
    }
}
