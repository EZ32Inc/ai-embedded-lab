/*
 * STM32G431CBU6 — Stage 2 Wiring Verify
 *
 * Mailbox-only loopback verification. No LA required.
 * Mailbox at 0x20007F00.
 *
 * Tests performed:
 *   [bit 0] ERR_GPIO_HIGH : PA8=H → PA6 read != H
 *   [bit 1] ERR_GPIO_LOW  : PA8=L → PA6 read != L
 *   [bit 2] ERR_UART      : PA9(TX)→PA10(RX) byte mismatch/timeout (USART1 AF7)
 *   [bit 3] ERR_ADC_HIGH  : PB1=H → PB0 ADC reading < 3000 (12-bit)
 *   [bit 4] ERR_ADC_LOW   : PB1=L → PB0 ADC reading > 1000 (12-bit)
 *
 * Bench wiring required:
 *   PA8 ↔ PA6   (GPIO loopback)
 *   PA9 ↔ PA10  (UART loopback, USART1 TX→RX)
 *   PB1 ↔ PB0   (ADC loopback: GPIO PB1 output drives ADC1_IN15 PB0)
 *
 * STM32G431 register map: RM0440.
 * Clock: 16 MHz HSI (default). SysTick: 1 ms per tick.
 */

#include <stdint.h>
#include "../ael_mailbox.h"

/* ---- RCC ---------------------------------------------------------------- */
#define RCC_BASE           0x40021000u
#define RCC_AHB2ENR        (*(volatile uint32_t *)(RCC_BASE + 0x4Cu))
#define RCC_APB2ENR        (*(volatile uint32_t *)(RCC_BASE + 0x60u))

#define RCC_AHB2ENR_GPIOAEN  (1u << 0)
#define RCC_AHB2ENR_GPIOBEN  (1u << 1)
#define RCC_AHB2ENR_ADC12EN  (1u << 13)
#define RCC_APB2ENR_USART1EN (1u << 14)

/* ---- GPIOA (AHB2, base 0x48000000) -------------------------------------- */
#define GPIOA_BASE  0x48000000u
#define GPIOA_MODER (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_IDR   (*(volatile uint32_t *)(GPIOA_BASE + 0x10u))
#define GPIOA_ODR   (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))
#define GPIOA_AFRH  (*(volatile uint32_t *)(GPIOA_BASE + 0x24u))

/* ---- GPIOB (AHB2, base 0x48000400) -------------------------------------- */
#define GPIOB_BASE  0x48000400u
#define GPIOB_MODER (*(volatile uint32_t *)(GPIOB_BASE + 0x00u))
#define GPIOB_ODR   (*(volatile uint32_t *)(GPIOB_BASE + 0x14u))

/* ---- SysTick ------------------------------------------------------------ */
#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

/* ---- USART1 (APB2, 0x40013800) — G431 new-style register map ----------- */
#define USART1_BASE  0x40013800u
#define USART1_CR1   (*(volatile uint32_t *)(USART1_BASE + 0x00u))
#define USART1_BRR   (*(volatile uint32_t *)(USART1_BASE + 0x0Cu))
#define USART1_ISR   (*(volatile uint32_t *)(USART1_BASE + 0x1Cu))
#define USART1_RDR   (*(volatile uint32_t *)(USART1_BASE + 0x24u))
#define USART1_TDR   (*(volatile uint32_t *)(USART1_BASE + 0x28u))
#define USART_ISR_RXNE (1u << 5)
#define USART_ISR_TXE  (1u << 7)
#define USART_CR1_RE   (1u << 2)
#define USART_CR1_TE   (1u << 3)
#define USART_CR1_UE   (1u << 0)

/* ---- ADC1 (AHB2-2, 0x50000000) — G431 register map --------------------- */
#define ADC1_BASE    0x50000000u
#define ADC1_ISR     (*(volatile uint32_t *)(ADC1_BASE + 0x00u))
#define ADC1_CR      (*(volatile uint32_t *)(ADC1_BASE + 0x08u))
#define ADC1_CFGR    (*(volatile uint32_t *)(ADC1_BASE + 0x0Cu))
#define ADC1_SMPR2   (*(volatile uint32_t *)(ADC1_BASE + 0x18u))
#define ADC1_SQR1    (*(volatile uint32_t *)(ADC1_BASE + 0x30u))
#define ADC1_DR      (*(volatile uint32_t *)(ADC1_BASE + 0x40u))
/* ADC12 common */
#define ADC12_CCR    (*(volatile uint32_t *)0x50000308u)

/* ---- Error bitmask ------------------------------------------------------ */
#define ERR_GPIO_HIGH  (1u << 0)
#define ERR_GPIO_LOW   (1u << 1)
#define ERR_UART       (1u << 2)
#define ERR_ADC_HIGH   (1u << 3)
#define ERR_ADC_LOW    (1u << 4)

/* ---- Delay -------------------------------------------------------------- */
static void delay_ms(uint32_t ms)
{
    for (uint32_t i = 0u; i < ms; i++) {
        SYST_CVR = 0u;
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

/* ---- GPIO loopback: PA8 (output) → PA6 (input) ------------------------- */
static uint32_t test_gpio_loopback(void)
{
    uint32_t err = 0u;

    /* PA8: output push-pull */
    GPIOA_MODER &= ~(0x3u << 16u);
    GPIOA_MODER |=  (0x1u << 16u);
    /* PA6: input floating */
    GPIOA_MODER &= ~(0x3u << 12u);

    GPIOA_ODR |= (1u << 8u);
    delay_ms(2u);
    if ((GPIOA_IDR & (1u << 6u)) == 0u) { err |= ERR_GPIO_HIGH; }

    GPIOA_ODR &= ~(1u << 8u);
    delay_ms(2u);
    if ((GPIOA_IDR & (1u << 6u)) != 0u) { err |= ERR_GPIO_LOW; }

    return err;
}

/* ---- UART loopback: PA9 (USART1_TX AF7) → PA10 (USART1_RX AF7) --------- */
static uint32_t test_uart_loopback(void)
{
    /* PA9 → AF7: MODER[19:18]=10, AFRH[7:4]=7 */
    GPIOA_MODER &= ~(0x3u << 18u);
    GPIOA_MODER |=  (0x2u << 18u);
    GPIOA_AFRH  &= ~(0xFu <<  4u);
    GPIOA_AFRH  |=  (0x7u <<  4u);
    /* PA10 → AF7: MODER[21:20]=10, AFRH[11:8]=7 */
    GPIOA_MODER &= ~(0x3u << 20u);
    GPIOA_MODER |=  (0x2u << 20u);
    GPIOA_AFRH  &= ~(0xFu <<  8u);
    GPIOA_AFRH  |=  (0x7u <<  8u);

    RCC_APB2ENR |= RCC_APB2ENR_USART1EN;
    (void)RCC_APB2ENR;

    /*
     * 115200 baud at 16 MHz HSI (16x oversampling):
     * BRR = 16e6 / 115200 = 139
     */
    USART1_CR1 = 0u;
    USART1_BRR = 139u;
    USART1_CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;

    uint32_t timeout = 1000000u;
    while ((USART1_ISR & USART_ISR_TXE) == 0u) {
        if (--timeout == 0u) { return ERR_UART; }
    }
    USART1_TDR = 0x5Au;

    timeout = 1000000u;
    while ((USART1_ISR & USART_ISR_RXNE) == 0u) {
        if (--timeout == 0u) { return ERR_UART; }
    }
    if ((uint8_t)(USART1_RDR & 0xFFu) != 0x5Au) {
        return ERR_UART;
    }

    return 0u;
}

/* ---- ADC loopback: PB1 (GPIO output) → PB0 (ADC1_IN15) ----------------- */
static uint32_t test_adc_loopback(void)
{
    uint32_t err = 0u;

    /* PB1: output push-pull */
    GPIOB_MODER &= ~(0x3u << 2u);
    GPIOB_MODER |=  (0x1u << 2u);
    /* PB0: analog (MODER[1:0]=11) → ADC1_IN15 */
    GPIOB_MODER |= (0x3u << 0u);

    /* ADC12 clock */
    RCC_AHB2ENR |= RCC_AHB2ENR_ADC12EN;
    (void)RCC_AHB2ENR;

    /* Synchronous clock CKMODE=01 (HCLK/1) */
    ADC12_CCR = (ADC12_CCR & ~(3u << 16)) | (1u << 16);

    /* Exit deep power down, enable regulator */
    ADC1_CR &= ~(1u << 29);   /* clear DEEPPWD */
    ADC1_CR |=  (1u << 28);   /* set ADVREGEN */

    /* Regulator startup (~20us) */
    for (volatile uint32_t i = 0u; i < 500u; i++) { (void)i; }

    /* Calibration (single-ended) */
    ADC1_CR &= ~(1u << 30);   /* ADCALDIF=0 */
    ADC1_CR |=  (1u << 31);   /* ADCAL */
    while ((ADC1_CR & (1u << 31)) != 0u) {}

    /* Enable ADC */
    ADC1_CR |= (1u << 0);     /* ADEN */
    while ((ADC1_ISR & (1u << 0)) == 0u) {}  /* wait ADRDY */

    /*
     * Channel 15 (PB0) — SMPR2 bits[17:15].
     * Set 640.5 cycles sample time (SMP=111b).
     */
    ADC1_SMPR2 |= (7u << 15);
    ADC1_SQR1   = (15u << 6);   /* SQ1=15 */
    ADC1_CFGR   = 0u;            /* single mode, right-aligned */

    /* --- HIGH: PB1=H → PB0 ADC should be near 4095 --- */
    GPIOB_ODR |= (1u << 1u);
    delay_ms(2u);
    {
        uint32_t timeout = 500000u;
        ADC1_ISR = (1u << 2);    /* clear EOC */
        ADC1_CR |= (1u << 2);    /* ADSTART */
        while (((ADC1_ISR & (1u << 2)) == 0u) && timeout-- > 0u) {}
        if ((ADC1_ISR & (1u << 2)) == 0u || ADC1_DR < 3000u) {
            err |= ERR_ADC_HIGH;
        }
    }

    /* --- LOW: PB1=L → PB0 ADC should be near 0 --- */
    GPIOB_ODR &= ~(1u << 1u);
    delay_ms(2u);
    {
        uint32_t timeout = 500000u;
        ADC1_ISR = (1u << 2);    /* clear EOC */
        ADC1_CR |= (1u << 2);    /* ADSTART */
        while (((ADC1_ISR & (1u << 2)) == 0u) && timeout-- > 0u) {}
        if ((ADC1_ISR & (1u << 2)) == 0u || ADC1_DR > 1000u) {
            err |= ERR_ADC_LOW;
        }
    }

    return err;
}

/* ---- Main --------------------------------------------------------------- */
int main(void)
{
    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    RCC_AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN;
    (void)RCC_AHB2ENR;

    ael_mailbox_init();

    uint32_t err = 0u;
    err |= test_gpio_loopback();
    err |= test_uart_loopback();
    err |= test_adc_loopback();

    if (err == 0u) {
        ael_mailbox_pass();
        uint32_t iteration = 0u;
        while (1) {
            delay_ms(1u);
            AEL_MAILBOX->detail0 = ++iteration;
        }
    } else {
        ael_mailbox_fail(err, 0u);
        while (1) {}
    }
}
