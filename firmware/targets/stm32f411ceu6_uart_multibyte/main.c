/*
 * STM32F401RCT6 — UART Multi-byte Loopback Test
 *
 * PA9 (USART1_TX, AF7) → PA10 (USART1_RX, AF7), 115200 8N1.
 * Sends 4 bytes {0x55, 0xAA, 0x12, 0x34} one at a time and verifies
 * each echoed byte individually.
 *
 * Mailbox at 0x2000FC00.
 *   PASS: all 4 bytes match. detail0 = heartbeat counter.
 *   FAIL: error_code bits 0-3 = which byte failed/timed out.
 *         detail0 = matched byte count (0–3).
 *
 * Register addresses: RM0368 (STM32F401 Reference Manual).
 * Clock: 16 MHz HSI. BRR=139 → 115108 baud (0.08% error).
 */

#include <stdint.h>
#include "ael_mailbox.h"

/* ---- RCC ---------------------------------------------------------------- */
#define RCC_BASE           0x40023800u
#define RCC_AHB1ENR        (*(volatile uint32_t *)(RCC_BASE + 0x30u))
#define RCC_APB2ENR        (*(volatile uint32_t *)(RCC_BASE + 0x44u))
#define RCC_AHB1ENR_GPIOAEN  (1u << 0)
#define RCC_APB2ENR_USART1EN (1u << 4)

/* ---- GPIOA -------------------------------------------------------------- */
#define GPIOA_BASE  0x40020000u
#define GPIOA_MODER (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_AFRH  (*(volatile uint32_t *)(GPIOA_BASE + 0x24u))

/* ---- USART1 (APB2, base 0x40011000) ------------------------------------- */
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

/* ---- SysTick ------------------------------------------------------------ */
#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

#define TX_TIMEOUT 1000000u

static const uint8_t TX_BYTES[4] = { 0x55u, 0xAAu, 0x12u, 0x34u };

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

    /* Enable GPIOA and USART1 clocks */
    RCC_AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    (void)RCC_AHB1ENR;
    RCC_APB2ENR |= RCC_APB2ENR_USART1EN;
    (void)RCC_APB2ENR;

    /*
     * PA9  → AF7 (USART1_TX): MODER[19:18]=10, AFRH[7:4]=7
     * PA10 → AF7 (USART1_RX): MODER[21:20]=10, AFRH[11:8]=7
     */
    GPIOA_MODER &= ~(0x3u << 18u);
    GPIOA_MODER |=  (0x2u << 18u);
    GPIOA_AFRH  &= ~(0xFu <<  4u);
    GPIOA_AFRH  |=  (0x7u <<  4u);

    GPIOA_MODER &= ~(0x3u << 20u);
    GPIOA_MODER |=  (0x2u << 20u);
    GPIOA_AFRH  &= ~(0xFu <<  8u);
    GPIOA_AFRH  |=  (0x7u <<  8u);

    /*
     * USART1: 115200 baud at 16 MHz HSI, OVER8=0.
     * USARTDIV = 16e6/(16*115200) = 8.6805 → mantissa=8, frac=11 → BRR=0x8B=139.
     */
    USART1_CR1 = 0u;
    USART1_BRR = 139u;
    USART1_CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;

    ael_mailbox_init();

    uint32_t err = 0u;
    uint32_t matched = 0u;

    for (uint32_t i = 0u; i < 4u; i++) {
        /* Wait for TXE, send byte */
        uint32_t timeout = TX_TIMEOUT;
        while ((USART1_SR & USART_SR_TXE) == 0u) {
            if (--timeout == 0u) { err |= (1u << i); goto done; }
        }
        USART1_DR = TX_BYTES[i];

        /* Wait for RXNE, verify byte */
        timeout = TX_TIMEOUT;
        while ((USART1_SR & USART_SR_RXNE) == 0u) {
            if (--timeout == 0u) { err |= (1u << i); goto done; }
        }
        uint8_t rx = (uint8_t)USART1_DR;
        if (rx != TX_BYTES[i]) {
            err |= (1u << i);
        } else {
            matched++;
        }
    }

done:
    if (err == 0u) {
        ael_mailbox_pass();
        uint32_t iteration = 0u;
        while (1) {
            delay_ms(1u);
            AEL_MAILBOX->detail0 = ++iteration;
        }
    } else {
        /*
         * FAIL bitmask (bits 0-3 = byte index that failed):
         *   bit 0: byte 0x55 failed
         *   bit 1: byte 0xAA failed
         *   bit 2: byte 0x12 failed
         *   bit 3: byte 0x34 failed
         * detail0 = matched byte count (0-3).
         */
        ael_mailbox_fail(err, matched);
        while (1) {}
    }
}
