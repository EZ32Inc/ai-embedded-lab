/*
 * STM32F103RCT6 — AEL USART1 loopback test
 *
 * Observable behaviour:
 *   - USART1: PA9 (TX, AF push-pull) → PA10 (RX, input floating)
 *   - Sends {0x55, 0xAA, 0x12, 0x34}, verifies echo
 *   - PASS after all 4 bytes matched
 *   - detail0 = matched count (0→4), increments after PASS
 *
 * Config: 8 MHz HSI, BRR=0x457 (~115200 baud), 8N1
 * Wiring required: PA9 → PA10
 * Mailbox address: 0x2000BC00
 *
 * Note: PA9/PA10 are safe on generic F103 boards (no ST-Link UART bridge
 * conflict, unlike STM32F4 Discovery).
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2000BC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE        0x40021000U
#define RCC_APB2ENR     (*(volatile uint32_t *)(RCC_BASE + 0x18U))

/* GPIOA (APB2) */
#define GPIOA_BASE      0x40010800U
#define GPIOA_CRH       (*(volatile uint32_t *)(GPIOA_BASE + 0x04U))

/* USART1 (APB2) */
#define USART1_BASE     0x40013800U
#define USART1_SR       (*(volatile uint32_t *)(USART1_BASE + 0x00U))
#define USART1_DR       (*(volatile uint32_t *)(USART1_BASE + 0x04U))
#define USART1_BRR      (*(volatile uint32_t *)(USART1_BASE + 0x08U))
#define USART1_CR1      (*(volatile uint32_t *)(USART1_BASE + 0x0CU))

#define USART_SR_TXE    (1U << 7)
#define USART_SR_RXNE   (1U << 5)
#define USART_SR_TC     (1U << 6)

#define TIMEOUT_USART   200000U

static uint32_t usart_transfer(uint8_t tx, uint8_t *rx_out)
{
    uint32_t t;

    /* Drain stale RXNE */
    if (USART1_SR & USART_SR_RXNE) { (void)USART1_DR; }

    /* Wait TXE */
    t = TIMEOUT_USART;
    while (!(USART1_SR & USART_SR_TXE)) { if (!--t) return 0U; }
    USART1_DR = tx;

    /* Wait RXNE */
    t = TIMEOUT_USART;
    while (!(USART1_SR & USART_SR_RXNE)) { if (!--t) return 0U; }
    *rx_out = (uint8_t)(USART1_DR & 0xFFU);

    return 1U;
}

int main(void)
{
    /* Enable GPIOA + USART1 clocks (APB2 bits 2 and 14) */
    RCC_APB2ENR |= (1U << 2) | (1U << 14);

    /*
     * PA9  (TX): AF push-pull 50 MHz → CRH[7:4]  = 0xB (CNF=10,MODE=11)
     * PA10 (RX): input floating      → CRH[11:8] = 0x4 (CNF=01,MODE=00)
     */
    GPIOA_CRH &= ~0xFF0U;
    GPIOA_CRH |=  0x4B0U;

    /* BRR: 8 MHz HSI / 115200 → mantissa=69, fraction=7 → 0x457 */
    USART1_BRR = 0x457U;
    USART1_CR1 = (1U << 13) | (1U << 3) | (1U << 2); /* UE | TE | RE */

    ael_mailbox_init();

    static const uint8_t TX_BYTES[4] = { 0x55U, 0xAAU, 0x12U, 0x34U };

    for (uint32_t i = 0U; i < 4U; i++) {
        uint8_t rx = 0U;
        if (!usart_transfer(TX_BYTES[i], &rx)) {
            ael_mailbox_fail(0x10U | i, i);
            while (1) {}
        }
        if (rx != TX_BYTES[i]) {
            ael_mailbox_fail(0x20U | i, rx);
            while (1) {}
        }
        AEL_MAILBOX->detail0 = i + 1U;
    }

    ael_mailbox_pass();

    while (1) {
        AEL_MAILBOX->detail0++;
        for (volatile uint32_t d = 0; d < 4000U; d++) __asm__ volatile ("nop");
    }

    return 0;
}
