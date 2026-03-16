#include <stdint.h>
#include "../ael_mailbox.h"

/* STM32G431 — GPIO on AHB2 */
#define RCC_BASE       0x40021000u
#define RCC_AHB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x4Cu))

#define GPIOA_BASE     0x48000000u
#define GPIOA_MODER    (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_OTYPER   (*(volatile uint32_t *)(GPIOA_BASE + 0x04u))
#define GPIOA_OSPEEDR  (*(volatile uint32_t *)(GPIOA_BASE + 0x08u))
#define GPIOA_ODR      (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))

#define GPIOB_BASE     0x48000400u
#define GPIOB_MODER    (*(volatile uint32_t *)(GPIOB_BASE + 0x00u))
#define GPIOB_OTYPER   (*(volatile uint32_t *)(GPIOB_BASE + 0x04u))
#define GPIOB_OSPEEDR  (*(volatile uint32_t *)(GPIOB_BASE + 0x08u))
#define GPIOB_PUPDR    (*(volatile uint32_t *)(GPIOB_BASE + 0x0Cu))
#define GPIOB_ODR      (*(volatile uint32_t *)(GPIOB_BASE + 0x14u))

/* ADC1 (AHB2) — G431 new ADC register map */
#define ADC1_BASE      0x50000000u
#define ADC1_ISR       (*(volatile uint32_t *)(ADC1_BASE + 0x00u))
#define ADC1_CR        (*(volatile uint32_t *)(ADC1_BASE + 0x08u))
#define ADC1_CFGR      (*(volatile uint32_t *)(ADC1_BASE + 0x0Cu))
#define ADC1_SMPR2     (*(volatile uint32_t *)(ADC1_BASE + 0x18u))
#define ADC1_SQR1      (*(volatile uint32_t *)(ADC1_BASE + 0x30u))
#define ADC1_DR        (*(volatile uint32_t *)(ADC1_BASE + 0x40u))

/* ADC12 common registers */
#define ADC12_CCR      (*(volatile uint32_t *)0x50000308u)

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

static void gpiob_set_output(uint32_t pin)
{
    const uint32_t sh = pin * 2u;
    GPIOB_MODER &= ~(0x3u << sh);
    GPIOB_MODER |=  (0x1u << sh);
    GPIOB_OTYPER &= ~(1u << pin);
    GPIOB_OSPEEDR |= (0x3u << sh);
    GPIOB_PUPDR &= ~(0x3u << sh);
}

static void gpiob_set_analog(uint32_t pin)
{
    /* Analog mode: MODER=11, PUPDR=00 */
    const uint32_t sh = pin * 2u;
    GPIOB_MODER |= (0x3u << sh);
    GPIOB_PUPDR &= ~(0x3u << sh);
}

static void adc1_init(void)
{
    /* PB0 = ADC1_IN15 (analog input) */
    gpiob_set_analog(0u);

    /* Enable ADC12 clock (AHB2ENR bit 13) */
    RCC_AHB2ENR |= (1u << 13);
    (void)RCC_AHB2ENR;

    /* Select synchronous clock CKMODE=01 (HCLK/1) — must be set before ADVREGEN */
    ADC12_CCR |= (1u << 16);

    /* Exit deep power down, enable internal voltage regulator */
    ADC1_CR &= ~(1u << 29);   /* clear DEEPPWD */
    ADC1_CR |=  (1u << 28);   /* set ADVREGEN */

    /* Wait for regulator startup (~20us at 16MHz ≈ 400 cycles) */
    for (volatile uint32_t i = 0u; i < 500u; i++) { (void)i; }

    /* Start calibration (single-ended) */
    ADC1_CR |= (1u << 31);    /* ADCAL */
    while ((ADC1_CR & (1u << 31)) != 0u) {}

    /* Enable ADC */
    ADC1_CR |= (1u << 0);     /* ADEN */
    while ((ADC1_ISR & (1u << 0)) == 0u) {}  /* wait ADRDY */

    /* Set sample time for channel 15: bits 17:15 of SMPR2 = 111 (640 cycles) */
    ADC1_SMPR2 |= (7u << 15);

    /* Single regular conversion, channel 15 */
    ADC1_SQR1 = (15u << 6);   /* L=0, SQ1=15 */
    ADC1_CFGR = 0u;            /* single mode (no CONT), right-aligned */
}

static uint8_t adc1_read(uint16_t *value_out)
{
    uint32_t timeout = 200000u;

    ADC1_ISR = (1u << 2);          /* clear EOC */
    ADC1_CR |= (1u << 2);          /* ADSTART */
    while (((ADC1_ISR & (1u << 2)) == 0u) && timeout-- > 0u) {}
    if ((ADC1_ISR & (1u << 2)) == 0u) { return 0u; }

    *value_out = (uint16_t)(ADC1_DR & 0xFFFFu);
    return 1u;
}

int main(void)
{
    uint32_t phase_ms  = 0u;
    uint32_t led_ms    = 0u;
    uint8_t phase_high = 0u;
    uint8_t adc_good   = 0u;
    uint8_t mb_settled = 0u;

    RCC_AHB2ENR |= (1u << 0) | (1u << 1);  /* GPIOAEN, GPIOBEN */
    (void)RCC_AHB2ENR;

    gpioa_set_output(2u);   /* PA2: signal output */
    gpioa_set_output(8u);   /* PA8: LED */
    gpiob_set_output(1u);   /* PB1: analog drive (→ PB0 loopback) */

    adc1_init();

    GPIOA_ODR &= ~((1u << 2) | (1u << 8));
    GPIOB_ODR &= ~(1u << 1);

    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = (1u << 2) | (1u << 0);
    ael_mailbox_init();

    while (1) {
        if ((SYST_CSR & (1u << 16)) == 0u) { continue; }

        phase_ms += 1u;
        led_ms   += 1u;

        if (phase_ms >= 5u) {
            uint16_t value = 0u;
            uint8_t ok;

            phase_ms = 0u;
            phase_high ^= 1u;

            if (phase_high != 0u) {
                GPIOB_ODR |= (1u << 1);   /* drive PB1 high */
            } else {
                GPIOB_ODR &= ~(1u << 1);  /* drive PB1 low */
            }

            ok = adc1_read(&value);
            if (phase_high != 0u) {
                adc_good = (uint8_t)(ok != 0u && value > 2500u);
            } else {
                adc_good = (uint8_t)(ok != 0u && value < 1000u);
            }
            if (mb_settled == 0u) {
                if (adc_good != 0u) { ael_mailbox_pass(); }
                else { ael_mailbox_fail(0xE001u, (uint32_t)value); }
                mb_settled = 1u;
            }

            if (adc_good != 0u && phase_high != 0u) {
                GPIOA_ODR |= (1u << 2);
            } else {
                GPIOA_ODR &= ~(1u << 2);
            }
        }

        if (led_ms >= (adc_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOA_ODR ^= (1u << 8);
        }
    }
}
