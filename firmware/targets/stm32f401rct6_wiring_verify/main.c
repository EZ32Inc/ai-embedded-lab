/*
 * STM32F401RCT6 — Stage 2 Wiring Verify
 *
 * Mailbox-only loopback verification. No LA required.
 * Mailbox at 0x2000FC00 (top 1 KB of 64 KB SRAM).
 *
 * Tests performed:
 *   [bit 0] ERR_GPIO_HIGH : PA8=H → PA6 read != H
 *   [bit 1] ERR_GPIO_LOW  : PA8=L → PA6 read != L
 *   [bit 2] ERR_UART      : PA9(TX)→PA10(RX) byte mismatch/timeout (USART1 AF7)
 *   [bit 3] ERR_ADC_HIGH  : PB0=H → PB1 ADC reading < 3000 (12-bit)
 *   [bit 4] ERR_ADC_LOW   : PB0=L → PB1 ADC reading > 1000 (12-bit)
 *
 * Bench wiring required:
 *   PA8 ↔ PA6   (GPIO loopback)
 *   PA9 ↔ PA10  (UART loopback, USART1 TX→RX)
 *   PB0 ↔ PB1   (ADC loopback: GPIO output drives ADC1_IN9)
 *
 * Register base addresses from RM0368 (STM32F401 Reference Manual).
 * Clock: 16 MHz HSI (no PLL). SysTick: 1 ms per tick at 16 MHz.
 */

#include <stdint.h>
#include "ael_mailbox.h"

/* ---- RCC (RM0368 §6) ---------------------------------------------------- */

#define RCC_BASE           0x40023800u
#define RCC_AHB1ENR        (*(volatile uint32_t *)(RCC_BASE + 0x30u))
#define RCC_APB2ENR        (*(volatile uint32_t *)(RCC_BASE + 0x44u))
#define RCC_AHB1ENR_GPIOAEN  (1u << 0)
#define RCC_AHB1ENR_GPIOBEN  (1u << 1)
#define RCC_APB2ENR_USART1EN (1u << 4)
#define RCC_APB2ENR_ADC1EN   (1u << 8)

/* ---- GPIOA (RM0368 §8, base 0x40020000) --------------------------------- */

#define GPIOA_BASE  0x40020000u
#define GPIOA_MODER (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_IDR   (*(volatile uint32_t *)(GPIOA_BASE + 0x10u))
#define GPIOA_ODR   (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))
#define GPIOA_AFRH  (*(volatile uint32_t *)(GPIOA_BASE + 0x24u))

/* ---- GPIOB (RM0368 §8, base 0x40020400) --------------------------------- */

#define GPIOB_BASE  0x40020400u
#define GPIOB_MODER (*(volatile uint32_t *)(GPIOB_BASE + 0x00u))
#define GPIOB_ODR   (*(volatile uint32_t *)(GPIOB_BASE + 0x14u))

/* ---- SysTick (ARMv7-M ARM) ---------------------------------------------- */

#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

/* ---- USART1 (RM0368 §19, APB2 base 0x40011000) -------------------------- */

#define USART1_BASE 0x40011000u
#define USART1_SR   (*(volatile uint32_t *)(USART1_BASE + 0x00u))
#define USART1_DR   (*(volatile uint32_t *)(USART1_BASE + 0x04u))
#define USART1_BRR  (*(volatile uint32_t *)(USART1_BASE + 0x08u))
#define USART1_CR1  (*(volatile uint32_t *)(USART1_BASE + 0x0Cu))
#define USART_SR_RXNE (1u << 5)
#define USART_SR_TXE  (1u << 7)
#define USART_CR1_RE  (1u << 2)
#define USART_CR1_TE  (1u << 3)
#define USART_CR1_UE  (1u << 13)

/* ---- ADC1 (RM0368 §11, APB2 base 0x40012000) ---------------------------- */

#define ADC1_BASE   0x40012000u
#define ADC1_SR     (*(volatile uint32_t *)(ADC1_BASE + 0x00u))
#define ADC1_CR2    (*(volatile uint32_t *)(ADC1_BASE + 0x08u))
#define ADC1_SMPR2  (*(volatile uint32_t *)(ADC1_BASE + 0x10u))
#define ADC1_SQR1   (*(volatile uint32_t *)(ADC1_BASE + 0x2Cu))
#define ADC1_SQR3   (*(volatile uint32_t *)(ADC1_BASE + 0x34u))
#define ADC1_DR     (*(volatile uint32_t *)(ADC1_BASE + 0x4Cu))
#define ADC_SR_EOC      (1u << 1)
#define ADC_CR2_ADON    (1u << 0)
#define ADC_CR2_SWSTART (1u << 30)

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

    /* PA8: output push-pull (MODER[17:16] = 01) */
    GPIOA_MODER &= ~(0x3u << 16u);
    GPIOA_MODER |=  (0x1u << 16u);

    /* PA6: input floating (MODER[13:12] = 00) */
    GPIOA_MODER &= ~(0x3u << 12u);

    /* Drive HIGH, settle 2 ms, read PA6 */
    GPIOA_ODR |= (1u << 8u);
    delay_ms(2u);
    if ((GPIOA_IDR & (1u << 6u)) == 0u) {
        err |= ERR_GPIO_HIGH;
    }

    /* Drive LOW, settle 2 ms, read PA6 */
    GPIOA_ODR &= ~(1u << 8u);
    delay_ms(2u);
    if ((GPIOA_IDR & (1u << 6u)) != 0u) {
        err |= ERR_GPIO_LOW;
    }

    return err;
}

/* ---- UART loopback: PA9 (USART1_TX) → PA10 (USART1_RX), AF7 ------------ */

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

    /* Enable USART1 clock */
    RCC_APB2ENR |= RCC_APB2ENR_USART1EN;
    (void)RCC_APB2ENR;

    /*
     * 115200 baud at 16 MHz HSI, OVER8=0 (16x oversampling):
     * USARTDIV = 16e6 / (16 * 115200) = 8.6805...
     * Mantissa = 8, Fraction = round(0.6805 * 16) = 11 → BRR = (8<<4)|11 = 0x8B = 139
     * Actual baud = 16e6 / (16 * 8.6875) = 115108 (0.08% error)
     */
    USART1_CR1 = 0u;
    USART1_BRR = 139u;
    USART1_CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;

    /* Wait TXE, send 0x5A */
    uint32_t timeout = 1000000u;
    while ((USART1_SR & USART_SR_TXE) == 0u) {
        if (--timeout == 0u) { return ERR_UART; }
    }
    USART1_DR = 0x5Au;

    /* Wait RXNE, verify byte */
    timeout = 1000000u;
    while ((USART1_SR & USART_SR_RXNE) == 0u) {
        if (--timeout == 0u) { return ERR_UART; }
    }
    if ((uint8_t)USART1_DR != 0x5Au) {
        return ERR_UART;
    }

    return 0u;
}

/* ---- ADC loopback: PB0 (GPIO output) → PB1 (ADC1_IN9) ------------------ */

static uint32_t test_adc_loopback(void)
{
    uint32_t err = 0u;

    /* PB0: output push-pull (MODER[1:0] = 01) */
    GPIOB_MODER &= ~(0x3u << 0u);
    GPIOB_MODER |=  (0x1u << 0u);

    /* PB1: analog mode (MODER[3:2] = 11) — ADC1_IN9 */
    GPIOB_MODER |= (0x3u << 2u);

    /* Enable ADC1 clock */
    RCC_APB2ENR |= RCC_APB2ENR_ADC1EN;
    (void)RCC_APB2ENR;

    /*
     * Configure ADC1: single conversion, channel 9 (PB1).
     * SMPR2[29:27] = 111b → 480-cycle sampling for stable reading.
     * ADCCLK = PCLK2/2 = 8 MHz (default prescaler, no PLL).
     */
    ADC1_CR2  = 0u;
    ADC1_SQR1 = 0u;               /* L=0000: 1 conversion */
    ADC1_SQR3 = 9u;               /* SQ1 = channel 9      */
    ADC1_SMPR2 |= (0x7u << 27u);  /* ch9: 480 cycles      */
    ADC1_CR2  = ADC_CR2_ADON;     /* enable ADC           */
    delay_ms(1u);                  /* stabilisation        */

    /* --- Measure HIGH: PB0=H → PB1 ADC should read near 4095 --- */
    GPIOB_ODR |= (1u << 0u);
    delay_ms(2u);
    ADC1_CR2 |= ADC_CR2_SWSTART;
    uint32_t timeout = 1000000u;
    while ((ADC1_SR & ADC_SR_EOC) == 0u) {
        if (--timeout == 0u) { err |= ERR_ADC_HIGH; goto adc_done; }
    }
    if (ADC1_DR < 3000u) { err |= ERR_ADC_HIGH; }

    /* --- Measure LOW: PB0=L → PB1 ADC should read near 0 --- */
    GPIOB_ODR &= ~(1u << 0u);
    delay_ms(2u);
    ADC1_CR2 |= ADC_CR2_SWSTART;
    timeout = 1000000u;
    while ((ADC1_SR & ADC_SR_EOC) == 0u) {
        if (--timeout == 0u) { err |= ERR_ADC_LOW; goto adc_done; }
    }
    if (ADC1_DR > 1000u) { err |= ERR_ADC_LOW; }

adc_done:
    return err;
}

/* ---- Main --------------------------------------------------------------- */

int main(void)
{
    /* SysTick at 1 kHz from 16 MHz HSI: RVR = 16e6/1e3 - 1 = 15999 */
    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    /* Enable GPIOA and GPIOB clocks */
    RCC_AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOBEN;
    (void)RCC_AHB1ENR;

    ael_mailbox_init();

    uint32_t err = 0u;
    err |= test_gpio_loopback();
    err |= test_uart_loopback();
    err |= test_adc_loopback();

    if (err == 0u) {
        ael_mailbox_pass();
        /*
         * PASS: increment detail0 each ms — two consecutive GDB reads
         * with increasing values prove the MCU is still running.
         */
        uint32_t iteration = 0u;
        while (1) {
            delay_ms(1u);
            AEL_MAILBOX->detail0 = ++iteration;
        }
    } else {
        /*
         * FAIL: error_code bitmask tells which wire(s) failed.
         *   bit 0: ERR_GPIO_HIGH  — PA8=H, PA6 read L (open or short to GND)
         *   bit 1: ERR_GPIO_LOW   — PA8=L, PA6 read H (short to VDD)
         *   bit 2: ERR_UART       — PA9→PA10 byte timeout or mismatch
         *   bit 3: ERR_ADC_HIGH   — PB0=H, PB1 ADC < 3000 (open or bad contact)
         *   bit 4: ERR_ADC_LOW    — PB0=L, PB1 ADC > 1000 (short to VDD)
         */
        ael_mailbox_fail(err, 0u);
        while (1) {}
    }
}
