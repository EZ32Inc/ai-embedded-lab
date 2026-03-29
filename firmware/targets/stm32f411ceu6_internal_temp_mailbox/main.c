#include <stdint.h>

#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE       0x40023800u
#define RCC_APB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x44u))

/* ADC common + ADC1 */
#define ADC1_BASE      0x40012000u
#define ADC1_SR        (*(volatile uint32_t *)(ADC1_BASE + 0x00u))
#define ADC1_CR1       (*(volatile uint32_t *)(ADC1_BASE + 0x04u))
#define ADC1_CR2       (*(volatile uint32_t *)(ADC1_BASE + 0x08u))
#define ADC1_SMPR1     (*(volatile uint32_t *)(ADC1_BASE + 0x0Cu))
#define ADC1_SQR1      (*(volatile uint32_t *)(ADC1_BASE + 0x2Cu))
#define ADC1_SQR3      (*(volatile uint32_t *)(ADC1_BASE + 0x34u))
#define ADC1_DR        (*(volatile uint32_t *)(ADC1_BASE + 0x4Cu))
#define ADC_CCR        (*(volatile uint32_t *)0x40012304u)

#define RCC_ADC1EN     (1u << 8)
#define ADC_SR_EOC     (1u << 1)
#define ADC_CR2_ADON   (1u << 0)
#define ADC_CR2_SWSTART (1u << 30)
#define ADC_CR2_EOCS   (1u << 10)
#define ADC_CCR_ADCPRE_0 (1u << 16)
#define ADC_CCR_TSVREFE (1u << 23)

#define ERR_ADC_TIMEOUT   0x10u
#define ERR_SAMPLE_ZERO   0x20u
#define ERR_SAMPLE_SAT    0x21u
#define ERR_SPREAD_ZERO   0x22u

static void delay_cycles(volatile uint32_t cycles)
{
    while (cycles-- > 0u) {
        __asm__ volatile ("nop");
    }
}

static void adc1_init_internal_temp(void)
{
    RCC_APB2ENR |= RCC_ADC1EN;
    (void)RCC_APB2ENR;

    ADC_CCR &= ~(3u << 16);
    ADC_CCR |= ADC_CCR_ADCPRE_0;
    ADC_CCR |= ADC_CCR_TSVREFE;

    /* Channel 18 sample time = 480 cycles, regular sequence length = 1. */
    ADC1_SMPR1 = (7u << 24);
    ADC1_SQR1 = 0u;
    ADC1_SQR3 = 18u;
    ADC1_CR1 = 0u;
    ADC1_CR2 = ADC_CR2_EOCS | ADC_CR2_ADON;

    /* Temperature sensor startup stabilization. */
    delay_cycles(200000u);
}

static uint8_t adc1_read(uint16_t *value_out)
{
    uint32_t timeout = 500000u;

    ADC1_SR = 0u;
    ADC1_CR2 |= ADC_CR2_SWSTART;
    while (((ADC1_SR & ADC_SR_EOC) == 0u) && timeout-- > 0u) {
    }
    if ((ADC1_SR & ADC_SR_EOC) == 0u) {
        return 0u;
    }

    *value_out = (uint16_t)(ADC1_DR & 0xFFFFu);
    return 1u;
}

int main(void)
{
    uint32_t sum = 0u;
    uint16_t min_sample = 0xFFFFu;
    uint16_t max_sample = 0u;

    ael_mailbox_init();
    adc1_init_internal_temp();

    for (uint32_t i = 0u; i < 8u; ++i) {
        uint16_t sample = 0u;
        if (adc1_read(&sample) == 0u) {
            ael_mailbox_fail(ERR_ADC_TIMEOUT, i);
            while (1) {
            }
        }

        sum += sample;
        if (sample < min_sample) {
            min_sample = sample;
        }
        if (sample > max_sample) {
            max_sample = sample;
        }
        AEL_MAILBOX->detail0 = ((uint32_t)max_sample << 16) | min_sample;
        delay_cycles(50000u);
    }

    {
        const uint16_t avg = (uint16_t)(sum / 8u);
        const uint16_t spread = (uint16_t)(max_sample - min_sample);
        AEL_MAILBOX->detail0 = ((uint32_t)spread << 16) | avg;

        if (avg == 0u) {
            ael_mailbox_fail(ERR_SAMPLE_ZERO, AEL_MAILBOX->detail0);
            while (1) {
            }
        }
        if (avg >= 4095u) {
            ael_mailbox_fail(ERR_SAMPLE_SAT, AEL_MAILBOX->detail0);
            while (1) {
            }
        }
        if (spread == 0u) {
            ael_mailbox_fail(ERR_SPREAD_ZERO, AEL_MAILBOX->detail0);
            while (1) {
            }
        }
    }

    ael_mailbox_pass();

    while (1) {
        AEL_MAILBOX->detail0 ^= 0x00010000u;
        delay_cycles(200000u);
    }
}
