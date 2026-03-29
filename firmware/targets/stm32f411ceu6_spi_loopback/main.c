/*
 * STM32F401RCT6 — SPI2 Loopback Test
 *
 * PB15 (SPI2_MOSI, AF5) → PB14 (SPI2_MISO, AF5), 1 wire loopback.
 * PB13 (SPI2_SCK,  AF5), PB12 (SPI2_NSS,  AF5) software-managed.
 *
 * Sends 8 bytes {0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80} and verifies
 * each echoed byte. SPI master, full-duplex, 500 kHz, 8-bit, CPOL=0 CPHA=0.
 *
 * Clock: 16 MHz HSI. APB1 = 16 MHz. SPI2 on APB1.
 * BR[2:0]=101 → fPCLK/64 = 250 kHz (safe for any wire length).
 *
 * Mailbox at 0x2000FC00.
 *   PASS: all 8 bytes match. detail0 = heartbeat counter.
 *   FAIL: error_code = bitmask of failed byte indices (bits 0–7).
 *         detail0 = matched byte count (0–7).
 *
 * Register addresses: RM0368 (STM32F401 Reference Manual).
 */

#include <stdint.h>
#include "ael_mailbox.h"

/* ---- RCC ---------------------------------------------------------------- */
#define RCC_BASE        0x40023800u
#define RCC_AHB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x30u))
#define RCC_APB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x40u))
#define RCC_AHB1ENR_GPIOBEN (1u << 1)
#define RCC_APB1ENR_SPI2EN  (1u << 14)

/* ---- GPIOB -------------------------------------------------------------- */
#define GPIOB_BASE  0x40020400u
#define GPIOB_MODER (*(volatile uint32_t *)(GPIOB_BASE + 0x00u))
#define GPIOB_OTYPER (*(volatile uint32_t *)(GPIOB_BASE + 0x04u))
#define GPIOB_OSPEEDR (*(volatile uint32_t *)(GPIOB_BASE + 0x08u))
#define GPIOB_PUPDR  (*(volatile uint32_t *)(GPIOB_BASE + 0x0Cu))
#define GPIOB_ODR   (*(volatile uint32_t *)(GPIOB_BASE + 0x14u))
#define GPIOB_AFRH  (*(volatile uint32_t *)(GPIOB_BASE + 0x24u))

/* ---- SPI2 (APB1, base 0x40003800) -------------------------------------- */
#define SPI2_BASE   0x40003800u
#define SPI2_CR1    (*(volatile uint32_t *)(SPI2_BASE + 0x00u))
#define SPI2_CR2    (*(volatile uint32_t *)(SPI2_BASE + 0x04u))
#define SPI2_SR     (*(volatile uint32_t *)(SPI2_BASE + 0x08u))
#define SPI2_DR     (*(volatile uint32_t *)(SPI2_BASE + 0x0Cu))

#define SPI_CR1_CPHA    (1u << 0)
#define SPI_CR1_CPOL    (1u << 1)
#define SPI_CR1_MSTR    (1u << 2)
#define SPI_CR1_BR_DIV64 (0x5u << 3)   /* fPCLK/64 = 250 kHz */
#define SPI_CR1_SPE     (1u << 6)
#define SPI_CR1_SSI     (1u << 8)
#define SPI_CR1_SSM     (1u << 9)
#define SPI_SR_RXNE     (1u << 0)
#define SPI_SR_TXE      (1u << 1)
#define SPI_SR_BSY      (1u << 7)

/* ---- SysTick ------------------------------------------------------------ */
#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

#define TX_TIMEOUT 1000000u

static const uint8_t TX_BYTES[8] = {
    0x01u, 0x02u, 0x04u, 0x08u, 0x10u, 0x20u, 0x40u, 0x80u
};

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

    /* Enable GPIOB and SPI2 clocks */
    RCC_AHB1ENR |= RCC_AHB1ENR_GPIOBEN;
    (void)RCC_AHB1ENR;
    RCC_APB1ENR |= RCC_APB1ENR_SPI2EN;
    (void)RCC_APB1ENR;

    /*
     * PB12 → NSS  (AF5): managed manually as GPIO output (NSS=high idle)
     * PB13 → SCK  (AF5): MODER[27:26]=10, AFRH[23:20]=5
     * PB14 → MISO (AF5): MODER[29:28]=10, AFRH[27:24]=5
     * PB15 → MOSI (AF5): MODER[31:30]=10, AFRH[31:28]=5
     *
     * PB12 as GPIO output push-pull, start HIGH (deselected).
     */

    /* PB12: output push-pull */
    GPIOB_MODER &= ~(0x3u << 24u);
    GPIOB_MODER |=  (0x1u << 24u);
    GPIOB_ODR   |=  (1u << 12u);   /* NSS high */

    /* PB13 SCK: AF5 */
    GPIOB_MODER &= ~(0x3u << 26u);
    GPIOB_MODER |=  (0x2u << 26u);
    GPIOB_AFRH  &= ~(0xFu << 20u);
    GPIOB_AFRH  |=  (0x5u << 20u);

    /* PB14 MISO: AF5 */
    GPIOB_MODER &= ~(0x3u << 28u);
    GPIOB_MODER |=  (0x2u << 28u);
    GPIOB_AFRH  &= ~(0xFu << 24u);
    GPIOB_AFRH  |=  (0x5u << 24u);

    /* PB15 MOSI: AF5 */
    GPIOB_MODER &= ~(0x3u << 30u);
    GPIOB_MODER |=  (0x2u << 30u);
    GPIOB_AFRH  &= ~(0xFu << 28u);
    GPIOB_AFRH  |=  (0x5u << 28u);

    /*
     * SPI2: master, SSM=1 SSI=1 (software NSS), 8-bit, CPOL=0 CPHA=0.
     * BR=101 → fPCLK/64 = 250 kHz.
     */
    SPI2_CR1 = SPI_CR1_MSTR | SPI_CR1_BR_DIV64 | SPI_CR1_SSM | SPI_CR1_SSI;
    SPI2_CR2 = 0u;
    SPI2_CR1 |= SPI_CR1_SPE;

    ael_mailbox_init();

    uint32_t err     = 0u;
    uint32_t matched = 0u;

    /* Assert NSS */
    GPIOB_ODR &= ~(1u << 12u);
    delay_ms(1u);

    for (uint32_t i = 0u; i < 8u; i++) {
        /* Wait TXE */
        uint32_t timeout = TX_TIMEOUT;
        while ((SPI2_SR & SPI_SR_TXE) == 0u) {
            if (--timeout == 0u) { err |= (1u << i); goto done; }
        }
        SPI2_DR = TX_BYTES[i];

        /* Wait RXNE */
        timeout = TX_TIMEOUT;
        while ((SPI2_SR & SPI_SR_RXNE) == 0u) {
            if (--timeout == 0u) { err |= (1u << i); goto done; }
        }
        uint8_t rx = (uint8_t)SPI2_DR;
        if (rx != TX_BYTES[i]) {
            err |= (1u << i);
        } else {
            matched++;
        }
    }

    /* Wait until not busy, then deassert NSS */
    {
        uint32_t timeout = TX_TIMEOUT;
        while ((SPI2_SR & SPI_SR_BSY) != 0u) {
            if (--timeout == 0u) { break; }
        }
    }

done:
    GPIOB_ODR |= (1u << 12u);   /* deassert NSS */

    if (err == 0u) {
        ael_mailbox_pass();
        uint32_t iteration = 0u;
        while (1) {
            delay_ms(1u);
            AEL_MAILBOX->detail0 = ++iteration;
        }
    } else {
        /*
         * FAIL bitmask (bits 0-7 = byte index that failed):
         *   bit N: TX_BYTES[N] echoed incorrectly or timed out.
         * detail0 = matched byte count (0-7).
         */
        ael_mailbox_fail(err, matched);
        while (1) {}
    }
}
