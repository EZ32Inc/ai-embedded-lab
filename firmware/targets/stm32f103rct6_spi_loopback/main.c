/*
 * STM32F103RCT6 — AEL SPI2 loopback test
 *
 * Observable behaviour:
 *   - SPI2 master sends {0xA5, 0x5A, 0xF0, 0x0F} on PB15 (MOSI)
 *   - Reads echo on PB14 (MISO) via loopback wire
 *   - PB13 = SCK (output only)
 *   - PASS after all 4 bytes matched
 *   - detail0 = matched count (0→4), increments after PASS
 *
 * Config: SPI2 APB1 8 MHz, master, 8-bit, mode 0, /256 (~31 kHz)
 * GPIO: F103 uses CRH (CNF/MODE), no AFRL/AFRH
 * Wiring required: PB15 (MOSI) → PB14 (MISO)
 * Mailbox address: 0x2000BC00
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2000BC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE        0x40021000U
#define RCC_APB2ENR     (*(volatile uint32_t *)(RCC_BASE + 0x18U))
#define RCC_APB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x1CU))

/* GPIOB (APB2) */
#define GPIOB_BASE      0x40010C00U
#define GPIOB_CRH       (*(volatile uint32_t *)(GPIOB_BASE + 0x04U))

/* SPI2 (APB1) */
#define SPI2_BASE       0x40003800U
#define SPI2_CR1        (*(volatile uint32_t *)(SPI2_BASE + 0x00U))
#define SPI2_SR         (*(volatile uint32_t *)(SPI2_BASE + 0x08U))
#define SPI2_DR         (*(volatile uint32_t *)(SPI2_BASE + 0x0CU))

#define SPI_SR_TXE      (1U << 1)
#define SPI_SR_RXNE     (1U << 0)
#define SPI_SR_BSY      (1U << 7)

#define TIMEOUT_SPI     200000U

static uint32_t spi_transfer(uint8_t tx, uint8_t *rx_out)
{
    uint32_t t;

    if (SPI2_SR & SPI_SR_RXNE) { (void)SPI2_DR; }

    t = TIMEOUT_SPI;
    while (!(SPI2_SR & SPI_SR_TXE)) { if (!--t) return 0U; }
    SPI2_DR = tx;

    t = TIMEOUT_SPI;
    while (!(SPI2_SR & SPI_SR_RXNE)) { if (!--t) return 0U; }
    *rx_out = (uint8_t)(SPI2_DR & 0xFFU);

    t = TIMEOUT_SPI;
    while (SPI2_SR & SPI_SR_BSY) { if (!--t) return 0U; }

    return 1U;
}

int main(void)
{
    /* Enable GPIOB (APB2 bit 3) + SPI2 (APB1 bit 14) clocks */
    RCC_APB2ENR |= (1U << 3);
    RCC_APB1ENR |= (1U << 14);

    /*
     * PB13 (SCK,  AF PP 50MHz): CRH[23:20] = 0xB
     * PB14 (MISO, input float): CRH[27:24] = 0x4
     * PB15 (MOSI, AF PP 50MHz): CRH[31:28] = 0xB
     */
    GPIOB_CRH &= ~0xFFF00000U;
    GPIOB_CRH |=  0xB4B00000U;

    /*
     * SPI2: MSTR=1, BR=111 (/256 ~31 kHz), SSM=1, SSI=1
     * DFF=0 (8-bit), CPOL=0, CPHA=0 (mode 0)
     */
    SPI2_CR1 = (1U << 2)  |   /* MSTR */
               (7U << 3)  |   /* BR[2:0] = /256 */
               (1U << 8)  |   /* SSI */
               (1U << 9);     /* SSM */
    SPI2_CR1 |= (1U << 6);    /* SPE */

    ael_mailbox_init();

    static const uint8_t TX_BYTES[4] = { 0xA5U, 0x5AU, 0xF0U, 0x0FU };

    for (uint32_t i = 0U; i < 4U; i++) {
        uint8_t rx = 0U;
        if (!spi_transfer(TX_BYTES[i], &rx)) {
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
