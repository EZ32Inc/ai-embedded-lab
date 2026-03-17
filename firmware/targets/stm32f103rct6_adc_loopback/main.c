/*
 * STM32F103RCT6 — AEL ADC loopback test
 *
 * Observable behaviour:
 *   - PA0 (GPIO output) drives high/low
 *   - PA1 (ADC1_IN1, analog) reads back
 *   - 5 successful high+low cycles required for PASS
 *   - Thresholds: high > 3000 counts, low < 500 counts (12-bit, 3.3V)
 *   - detail0 = pass_count
 *
 * ADC config: PCLK2/2 = 4 MHz, 239.5-cycle sample time, software trigger
 * Wiring required: PA0 → PA1
 * Mailbox address: 0x2000BC00
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2000BC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE        0x40021000U
#define RCC_CFGR        (*(volatile uint32_t *)(RCC_BASE + 0x04U))
#define RCC_APB2ENR     (*(volatile uint32_t *)(RCC_BASE + 0x18U))

/* GPIOA (APB2) */
#define GPIOA_BASE      0x40010800U
#define GPIOA_CRL       (*(volatile uint32_t *)(GPIOA_BASE + 0x00U))
#define GPIOA_ODR       (*(volatile uint32_t *)(GPIOA_BASE + 0x0CU))

/* ADC1 (APB2) */
#define ADC1_BASE       0x40012400U
#define ADC1_SR         (*(volatile uint32_t *)(ADC1_BASE + 0x00U))
#define ADC1_CR1        (*(volatile uint32_t *)(ADC1_BASE + 0x04U))
#define ADC1_CR2        (*(volatile uint32_t *)(ADC1_BASE + 0x08U))
#define ADC1_SMPR2      (*(volatile uint32_t *)(ADC1_BASE + 0x10U))
#define ADC1_SQR1       (*(volatile uint32_t *)(ADC1_BASE + 0x2CU))
#define ADC1_SQR3       (*(volatile uint32_t *)(ADC1_BASE + 0x34U))
#define ADC1_DR         (*(volatile uint32_t *)(ADC1_BASE + 0x4CU))

#define ADC_SR_EOC      (1U << 1)
#define ADC_CR2_ADON    (1U << 0)
#define ADC_CR2_RSTCAL  (1U << 3)
#define ADC_CR2_CAL     (1U << 2)
#define ADC_CR2_EXTTRIG (1U << 20)
#define ADC_CR2_SWSTART (1U << 22)

#define ADC_HIGH_MIN    3000U
#define ADC_LOW_MAX     500U
#define DELAY_1MS       4000U

static void delay(uint32_t n)
{
    while (n--) __asm__ volatile ("nop");
}

static uint32_t adc_read(void)
{
    ADC1_SR &= ~ADC_SR_EOC;
    ADC1_CR2 |= ADC_CR2_SWSTART;
    uint32_t t = 400000U;
    while (!(ADC1_SR & ADC_SR_EOC) && t--) {}
    return ADC1_DR & 0xFFFU;
}

int main(void)
{
    /* ADC prescaler: PCLK2/2 = 4 MHz — RCC_CFGR bits [15:14] = 00 (default) */
    RCC_CFGR &= ~(3U << 14);

    /* Enable GPIOA + ADC1 clocks (APB2 bits 2 and 9) */
    RCC_APB2ENR |= (1U << 2) | (1U << 9);

    /*
     * PA0: output push-pull 50 MHz → CRL[3:0]  = 0x3
     * PA1: analog input             → CRL[7:4]  = 0x0 (CNF=00,MODE=00)
     */
    GPIOA_CRL &= ~0xFFU;
    GPIOA_CRL |=  0x03U;   /* PA1 bits already 0x0 after mask */
    GPIOA_ODR &= ~(1U << 0);

    /* ADC1 config */
    ADC1_CR1  = 0U;                          /* 12-bit, no scan */
    ADC1_CR2  = ADC_CR2_ADON |
                (7U << 17)   |               /* EXTSEL=111 = SWSTART */
                ADC_CR2_EXTTRIG;
    ADC1_SMPR2 = (7U << 3);                  /* CH1: 239.5 cycles (bits [5:3]) */
    ADC1_SQR1  = 0U;                         /* L=0: 1 conversion */
    ADC1_SQR3  = 1U;                         /* SQ1 = channel 1 (PA1) */

    /* Calibration */
    for (volatile uint32_t i = 0; i < 200U; i++) __asm__ volatile ("nop");
    ADC1_CR2 |= ADC_CR2_RSTCAL;
    while (ADC1_CR2 & ADC_CR2_RSTCAL) {}
    ADC1_CR2 |= ADC_CR2_CAL;
    while (ADC1_CR2 & ADC_CR2_CAL) {}

    ael_mailbox_init();

    uint32_t pass_count = 0U;

    while (1) {
        /* Drive PA0 high, read ADC */
        GPIOA_ODR |= (1U << 0);
        delay(DELAY_1MS);
        uint32_t val_high = adc_read();

        /* Drive PA0 low, read ADC */
        GPIOA_ODR &= ~(1U << 0);
        delay(DELAY_1MS);
        uint32_t val_low = adc_read();

        if (val_high < ADC_HIGH_MIN) {
            ael_mailbox_fail(0x01U, val_high);
            while (1) {}
        }
        if (val_low > ADC_LOW_MAX) {
            ael_mailbox_fail(0x02U, val_low);
            while (1) {}
        }

        pass_count++;
        AEL_MAILBOX->detail0 = pass_count;

        if (pass_count >= 5U) {
            ael_mailbox_pass();
            while (1) {
                delay(DELAY_1MS);
                AEL_MAILBOX->detail0++;
            }
        }
    }

    return 0;
}
