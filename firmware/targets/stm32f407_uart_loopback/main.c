/*
 * STM32F407 Discovery — AEL UART loopback test
 *
 * Observable behaviour:
 *   - USART2 sends {0x55, 0xAA, 0x12, 0x34} on PD5 (TX)
 *   - Receives same bytes on PD6 (RX) via loopback wire
 *   - PASS after all 4 bytes matched
 *   - detail0 = matched byte count (0→4), increments after PASS to show liveness
 *
 * Configuration: 115200 8N1 at 16 MHz HSI, USART2 on APB1
 * Wiring required: PD5 → PD6 (jumper wire)
 * Mailbox address: 0x2001FC00 (SRAM1 top -1 KB)
 *
 * Note: uses USART2/PD5/PD6 instead of USART1/PA9/PA10 because on some
 * STM32F4 Discovery revisions PA9/PA10 are wired to the ST-Link UART
 * bridge, which prevents self-loopback on those pins.
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2001FC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE         0x40023800U
#define RCC_AHB1ENR      (*(volatile uint32_t *)(RCC_BASE + 0x30U))
#define RCC_APB1ENR      (*(volatile uint32_t *)(RCC_BASE + 0x40U))

/* GPIOD */
#define GPIOD_BASE       0x40020C00U
#define GPIOD_MODER      (*(volatile uint32_t *)(GPIOD_BASE + 0x00U))
#define GPIOD_AFRL       (*(volatile uint32_t *)(GPIOD_BASE + 0x20U))

/* USART2 on APB1 */
#define USART2_BASE      0x40004400U
#define USART2_SR        (*(volatile uint32_t *)(USART2_BASE + 0x00U))
#define USART2_DR        (*(volatile uint32_t *)(USART2_BASE + 0x04U))
#define USART2_BRR       (*(volatile uint32_t *)(USART2_BASE + 0x08U))
#define USART2_CR1       (*(volatile uint32_t *)(USART2_BASE + 0x0CU))

#define USART_SR_TXE     (1U << 7)
#define USART_SR_RXNE    (1U << 5)
#define USART_CR1_UE     (1U << 13)
#define USART_CR1_TE     (1U << 3)
#define USART_CR1_RE     (1U << 2)

/*
 * 115200 baud at 16 MHz HSI, APB1 = HCLK = 16 MHz (default at reset), OVER8=0:
 *   USARTDIV = 16 MHz / (16 * 115200) = 8.6805...
 *   BRR = (8 << 4) | 11 = 0x8B
 */
#define USART2_BRR_VAL   0x8BU

/* RX timeout: ~10 ms at 16 MHz */
#define TIMEOUT_RX  160000U

static uint32_t usart_rx_wait(void)
{
    uint32_t t = TIMEOUT_RX;
    while (!(USART2_SR & USART_SR_RXNE)) {
        if (--t == 0U) {
            return 0xFFFFFFFFU;
        }
    }
    return USART2_DR & 0xFFU;
}

int main(void)
{
    /* Enable GPIOD (AHB1 bit 3) + USART2 (APB1 bit 17) clocks */
    RCC_AHB1ENR |= (1U << 3);
    RCC_APB1ENR |= (1U << 17);

    /*
     * PD5 (USART2_TX, AF7): MODER[11:10] = 10
     * PD6 (USART2_RX, AF7): MODER[13:12] = 10
     */
    GPIOD_MODER &= ~(0xFU << 10);
    GPIOD_MODER |=  (0xAU << 10);

    /*
     * AFRL: PD5[23:20] = AF7, PD6[27:24] = AF7
     */
    GPIOD_AFRL &= ~(0xFFU << 20);
    GPIOD_AFRL |=  (0x77U << 20);

    /* Configure USART2: 115200 8N1 */
    USART2_BRR = USART2_BRR_VAL;
    USART2_CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;

    ael_mailbox_init();

    static const uint8_t TX_BYTES[4] = { 0x55U, 0xAAU, 0x12U, 0x34U };

    for (uint32_t i = 0; i < 4U; i++) {
        while (!(USART2_SR & USART_SR_TXE)) {}
        USART2_DR = TX_BYTES[i];

        uint32_t rx = usart_rx_wait();

        if (rx == 0xFFFFFFFFU) {
            ael_mailbox_fail(0x10U | i, i);
            while (1) {}
        }

        if ((uint8_t)rx != TX_BYTES[i]) {
            ael_mailbox_fail(0x20U | i, rx);
            while (1) {}
        }

        AEL_MAILBOX->detail0 = i + 1U;
    }

    ael_mailbox_pass();

    while (1) {
        AEL_MAILBOX->detail0++;
        for (volatile uint32_t d = 0; d < 4000U; d++) {
            __asm__ volatile ("nop");
        }
    }

    return 0;
}
