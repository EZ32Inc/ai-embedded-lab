/*
 * STM32F407 Discovery — AEL SPI loopback test
 *
 * Observable behaviour:
 *   - SPI2 master sends {0xA5, 0x5A, 0xF0, 0x0F} on PB15 (MOSI)
 *   - Reads echo on PB14 (MISO) via loopback wire
 *   - PB13 = SCK (output only, no loopback needed)
 *   - PASS after all 4 bytes matched
 *   - detail0 = matched byte count (0→4), increments after PASS
 *
 * Configuration: SPI2, master, 8-bit, mode 0, /256 (~62 kHz at 16 MHz HSI)
 * Wiring required: PB15 (MOSI) → PB14 (MISO)
 * Mailbox address: 0x2001FC00 (SRAM1 top -1 KB)
 */

#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x2001FC00u
#include "ael_mailbox.h"

/* RCC */
#define RCC_BASE        0x40023800U
#define RCC_AHB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x30U))
#define RCC_APB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x40U))

/* GPIOB */
#define GPIOB_BASE      0x40020400U
#define GPIOB_MODER     (*(volatile uint32_t *)(GPIOB_BASE + 0x00U))
#define GPIOB_OSPEEDR   (*(volatile uint32_t *)(GPIOB_BASE + 0x08U))
#define GPIOB_AFRH      (*(volatile uint32_t *)(GPIOB_BASE + 0x24U))

/* SPI2 (classic F4, APB1) */
#define SPI2_BASE       0x40003800U
#define SPI2_CR1        (*(volatile uint32_t *)(SPI2_BASE + 0x00U))
#define SPI2_SR         (*(volatile uint32_t *)(SPI2_BASE + 0x08U))
#define SPI2_DR         (*(volatile uint32_t *)(SPI2_BASE + 0x0CU))

#define SPI_SR_TXE      (1U << 1)
#define SPI_SR_RXNE     (1U << 0)
#define SPI_SR_BSY      (1U << 7)

/* TX timeout */
#define TIMEOUT_SPI     200000U

static uint32_t spi_transfer(uint8_t tx, uint8_t *rx_out)
{
    uint32_t t;

    /* Drain any stale RXNE */
    if (SPI2_SR & SPI_SR_RXNE) { (void)SPI2_DR; }

    /* Wait TXE */
    t = TIMEOUT_SPI;
    while (!(SPI2_SR & SPI_SR_TXE)) { if (!--t) return 0U; }
    SPI2_DR = tx;

    /* Wait RXNE */
    t = TIMEOUT_SPI;
    while (!(SPI2_SR & SPI_SR_RXNE)) { if (!--t) return 0U; }
    *rx_out = (uint8_t)(SPI2_DR & 0xFFU);

    /* Wait not busy */
    t = TIMEOUT_SPI;
    while (SPI2_SR & SPI_SR_BSY) { if (!--t) return 0U; }

    return 1U;
}

int main(void)
{
    /* Enable GPIOB (AHB1 bit 1) + SPI2 (APB1 bit 14) clocks */
    RCC_AHB1ENR |= (1U << 1);
    RCC_APB1ENR |= (1U << 14);

    /*
     * PB13 (SCK, AF5):  MODER[27:26]=10, AFRH[23:20]=5
     * PB14 (MISO, AF5): MODER[29:28]=10, AFRH[27:24]=5
     * PB15 (MOSI, AF5): MODER[31:30]=10, AFRH[31:28]=5
     */
    GPIOB_MODER   &= ~0xFC000000U;
    GPIOB_MODER   |=  0xA8000000U;   /* all three pins = AF (10) */
    GPIOB_OSPEEDR |=  0xFC000000U;   /* high speed */
    GPIOB_AFRH    &= ~0xFFF00000U;
    GPIOB_AFRH    |=  0x55500000U;   /* PB13/14/15 = AF5 */

    /*
     * SPI2 config (classic F4):
     *   MSTR=1, BR=111 (/256 → ~62 kHz), SSM=1, SSI=1
     *   DFF=0 (8-bit), CPOL=0, CPHA=0 (mode 0)
     */
    SPI2_CR1 = (1U << 2)  |  /* MSTR */
               (7U << 3)  |  /* BR[2:0] = /256 */
               (1U << 8)  |  /* SSI */
               (1U << 9);    /* SSM */
    SPI2_CR1 |= (1U << 6);   /* SPE — enable after config */

    ael_mailbox_init();

    static const uint8_t TX_BYTES[4] = { 0xA5U, 0x5AU, 0xF0U, 0x0FU };

    for (uint32_t i = 0; i < 4U; i++) {
        uint8_t rx = 0U;
        if (!spi_transfer(TX_BYTES[i], &rx)) {
            /* Timeout: error_code = 0x10 | byte_index */
            ael_mailbox_fail(0x10U | i, i);
            while (1) {}
        }
        if (rx != TX_BYTES[i]) {
            /* Mismatch: error_code = 0x20 | byte_index, detail0 = received byte */
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
