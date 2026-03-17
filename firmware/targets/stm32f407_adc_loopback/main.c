/*
 * STM32F407 Discovery — AEL ADC loopback test
 *
 * Observable behaviour:
 *   - PC0 (output) drives high/low, PC1 (ADC1_IN11, analog) reads back
 *   - 5 successful high+low cycles required for PASS
 *   - Thresholds: high > 3000 counts, low < 500 counts (12-bit, 3.3V ref)
 *   - detail0 = pass_count, keeps incrementing after PASS
 *
 * Exercises: RCC, GPIOC, ADC1 classic register map, single software-start conversion.
 * Wiring required: PC0 → PC1 (jumper wire)
 * Mailbox address: 0x2001FC00 (SRAM1 top -1 KB)
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2001FC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE        0x40023800U
#define RCC_AHB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x30U))
#define RCC_APB2ENR     (*(volatile uint32_t *)(RCC_BASE + 0x44U))

/* GPIOC */
#define GPIOC_BASE      0x40020800U
#define GPIOC_MODER     (*(volatile uint32_t *)(GPIOC_BASE + 0x00U))
#define GPIOC_ODR       (*(volatile uint32_t *)(GPIOC_BASE + 0x14U))
#define GPIOC_PUPDR     (*(volatile uint32_t *)(GPIOC_BASE + 0x0CU))

/* ADC1 (classic F4 register map) */
#define ADC1_BASE       0x40012000U
#define ADC1_SR         (*(volatile uint32_t *)(ADC1_BASE + 0x00U))
#define ADC1_CR1        (*(volatile uint32_t *)(ADC1_BASE + 0x04U))
#define ADC1_CR2        (*(volatile uint32_t *)(ADC1_BASE + 0x08U))
#define ADC1_SMPR1      (*(volatile uint32_t *)(ADC1_BASE + 0x0CU))
#define ADC1_SQR1       (*(volatile uint32_t *)(ADC1_BASE + 0x2CU))
#define ADC1_SQR3       (*(volatile uint32_t *)(ADC1_BASE + 0x34U))
#define ADC1_DR         (*(volatile uint32_t *)(ADC1_BASE + 0x4CU))

/* ADC common (prescaler) */
#define ADC_CCR         (*(volatile uint32_t *)0x40012304U)

#define ADC1_SR_EOC     (1U << 1)
#define ADC1_CR2_ADON   (1U << 0)
#define ADC1_CR2_SWSTART (1U << 30)

/* Thresholds (12-bit, VDD=3.3V) */
#define ADC_HIGH_MIN    3000U
#define ADC_LOW_MAX     500U

/* ~1 ms at 16 MHz HSI */
#define DELAY_1MS       4000U

static void delay(uint32_t n)
{
    while (n--) __asm__ volatile ("nop");
}

static uint32_t adc_read(void)
{
    ADC1_SR &= ~ADC1_SR_EOC;         /* clear EOC */
    ADC1_CR2 |= ADC1_CR2_SWSTART;    /* start conversion */
    uint32_t t = 400000U;
    while (!(ADC1_SR & ADC1_SR_EOC) && t--) {}
    return ADC1_DR & 0xFFFU;
}

int main(void)
{
    /* Enable GPIOC (AHB1 bit 2) + ADC1 (APB2 bit 8) clocks */
    RCC_AHB1ENR |= (1U << 2);
    RCC_APB2ENR |= (1U << 8);

    /* PC0: output push-pull (GPIO driver) */
    GPIOC_MODER &= ~(3U << 0);
    GPIOC_MODER |=  (1U << 0);
    GPIOC_ODR   &= ~(1U << 0);   /* start low */

    /* PC1: analog input, no pull */
    GPIOC_MODER &= ~(3U << 2);
    GPIOC_MODER |=  (3U << 2);   /* analog = 11 */
    GPIOC_PUPDR &= ~(3U << 2);   /* no pull */

    /*
     * ADC1 config (classic F4):
     *   - ADCPRE = /2 → ADC clock = 8 MHz (≤ 36 MHz max)
     *   - 12-bit resolution (default, CR1 RES=00)
     *   - Single conversion, software start (EXTEN=00)
     *   - Channel 11 (PC1), 480-cycle sample time
     */
    ADC_CCR &= ~(3U << 16);       /* ADCPRE = /2 */
    ADC1_CR1  = 0U;               /* 12-bit, no scan */
    ADC1_CR2  = 0U;               /* single, no ext trigger */
    ADC1_SMPR1 = (7U << 3);       /* CH11: 480 cycles (bits [5:3]) */
    ADC1_SQR1  = 0U;              /* L=0: 1 conversion */
    ADC1_SQR3  = 11U;             /* SQ1 = channel 11 (PC1) */

    /* Enable ADC, wait tSTAB */
    ADC1_CR2 |= ADC1_CR2_ADON;
    for (volatile uint32_t i = 0; i < 200U; i++) __asm__ volatile ("nop");

    ael_mailbox_init();

    uint32_t pass_count = 0U;

    while (1) {
        /* Drive PC0 high, wait, read ADC */
        GPIOC_ODR |= (1U << 0);
        delay(DELAY_1MS);
        uint32_t val_high = adc_read();

        /* Drive PC0 low, wait, read ADC */
        GPIOC_ODR &= ~(1U << 0);
        delay(DELAY_1MS);
        uint32_t val_low = adc_read();

        if (val_high < ADC_HIGH_MIN) {
            /* High-state read too low: error_code = ADC value */
            ael_mailbox_fail(0x01U, val_high);
            while (1) {}
        }
        if (val_low > ADC_LOW_MAX) {
            /* Low-state read too high: error_code = ADC value */
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
