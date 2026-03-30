#include <stdint.h>
#include "../ael_mailbox.h"

/*
 * STM32G431CBU6 — Internal Temperature Sensor Mailbox Test
 *
 * ADC1 samples the internal temperature sensor (channel 16, VSENSESEL).
 * G431 ADC base: 0x50000000 (AHB2-2 domain, clock via RCC_AHB2ENR bit13).
 * ADC12_CCR at 0x50000308: CKMODE=01 (bits17:16), VSENSESEL (bit22).
 * Startup sequence: DEEPPWD→clear, ADVREGEN→set, calibrate, ADEN.
 *
 * Pass criteria: 8 samples, non-zero avg, avg < 4095, non-zero spread.
 * Mailbox at 0x20007F00.
 *   PASS: avg and spread valid. detail0[31:16]=spread, detail0[15:0]=avg.
 *   FAIL: error_code ERR_ADC_TIMEOUT/ERR_SAMPLE_ZERO/ERR_SAMPLE_SAT/ERR_SPREAD_ZERO.
 */

/* RCC */
#define RCC_BASE       0x40021000u
#define RCC_AHB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x4Cu))

/* ADC1 — G431 register map (base 0x50000000) */
#define ADC1_BASE      0x50000000u
#define ADC1_ISR       (*(volatile uint32_t *)(ADC1_BASE + 0x00u))
#define ADC1_CR        (*(volatile uint32_t *)(ADC1_BASE + 0x08u))
#define ADC1_CFGR      (*(volatile uint32_t *)(ADC1_BASE + 0x0Cu))
#define ADC1_SMPR2     (*(volatile uint32_t *)(ADC1_BASE + 0x18u))
#define ADC1_SQR1      (*(volatile uint32_t *)(ADC1_BASE + 0x30u))
#define ADC1_DR        (*(volatile uint32_t *)(ADC1_BASE + 0x40u))

/* ADC12 common registers */
#define ADC12_CCR      (*(volatile uint32_t *)0x50000308u)

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
    /* Enable ADC12 clock (AHB2ENR bit 13) */
    RCC_AHB2ENR |= (1u << 13);
    (void)RCC_AHB2ENR;

    /* Synchronous clock CKMODE=01 (HCLK/1): bits[17:16]=01 */
    ADC12_CCR = (ADC12_CCR & ~(3u << 16)) | (1u << 16);

    /* Enable temperature sensor: VSENSESEL=bit22 */
    ADC12_CCR |= (1u << 22);

    /* Exit deep power down, enable internal voltage regulator */
    ADC1_CR &= ~(1u << 29);   /* clear DEEPPWD */
    ADC1_CR |=  (1u << 28);   /* set ADVREGEN */

    /* Wait for regulator startup (~20us at 16MHz ≈ 320 cycles) */
    delay_cycles(500u);

    /* Start calibration (single-ended: ADCALDIF=0) */
    ADC1_CR &= ~(1u << 30);   /* ADCALDIF=0 (single-ended) */
    ADC1_CR |=  (1u << 31);   /* ADCAL */
    while ((ADC1_CR & (1u << 31)) != 0u) {}

    /* Enable ADC */
    ADC1_CR |= (1u << 0);     /* ADEN */
    while ((ADC1_ISR & (1u << 0)) == 0u) {}  /* wait ADRDY */

    /*
     * Temperature sensor = ADC1 channel 16.
     * SMPR2 covers channels 10-18: CH16 bits [20:18].
     * Set 640.5 cycles sample time (SMP=111b).
     */
    ADC1_SMPR2 |= (7u << 18);

    /* Single regular conversion, channel 16: SQ1[4:0] at bits[10:6] */
    ADC1_SQR1 = (16u << 6);

    /* Single mode, right-aligned */
    ADC1_CFGR = 0u;
}

static uint8_t adc1_read(uint16_t *value_out)
{
    uint32_t timeout = 500000u;

    ADC1_ISR = (1u << 2);         /* clear EOC */
    ADC1_CR  |= (1u << 2);        /* ADSTART */
    while (((ADC1_ISR & (1u << 2)) == 0u) && timeout-- > 0u) {}
    if ((ADC1_ISR & (1u << 2)) == 0u) {
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
            while (1) {}
        }

        sum += sample;
        if (sample < min_sample) { min_sample = sample; }
        if (sample > max_sample) { max_sample = sample; }
        AEL_MAILBOX->detail0 = ((uint32_t)max_sample << 16) | min_sample;
        delay_cycles(50000u);
    }

    {
        const uint16_t avg    = (uint16_t)(sum / 8u);
        const uint16_t spread = (uint16_t)(max_sample - min_sample);
        AEL_MAILBOX->detail0  = ((uint32_t)spread << 16) | avg;

        if (avg == 0u) {
            ael_mailbox_fail(ERR_SAMPLE_ZERO, AEL_MAILBOX->detail0);
            while (1) {}
        }
        if (avg >= 4095u) {
            ael_mailbox_fail(ERR_SAMPLE_SAT, AEL_MAILBOX->detail0);
            while (1) {}
        }
        if (spread == 0u) {
            ael_mailbox_fail(ERR_SPREAD_ZERO, AEL_MAILBOX->detail0);
            while (1) {}
        }
    }

    ael_mailbox_pass();

    while (1) {
        AEL_MAILBOX->detail0 ^= 0x00010000u;
        delay_cycles(200000u);
    }
}
