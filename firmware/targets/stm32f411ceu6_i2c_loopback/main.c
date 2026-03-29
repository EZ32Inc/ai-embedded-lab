/*
 * STM32F411CEU6 — I2C1 Master / I2C2 Slave Loopback
 *
 * I2C1 master: PB6 (SCL, AF4), PB7 (SDA, AF4)
 * I2C2 slave:  PB10(SCL, AF4), PB3 (SDA, AF9)
 *
 * PB3 is the alternate I2C2_SDA pin (AF9) used because PB11 (AF4) is not
 * exposed on the BlackPill connector.
 *
 * External wiring required: PB6↔PB10 (SCL bus), PB7↔PB3 (SDA bus).
 * Pull-up: STM32 internal ~40 kΩ via PUPDR=01 on all four pins.
 *
 * Status: SUSPENDED — hardware issue suspected (SDA wire anomaly).
 * See docs/reports/stm32f411ceu6_i2c_loopback_debug_2026-03-29.md
 *
 * Protocol:
 *   1. Master WRITE: send tx_buf[4] = {0xA1,0xB2,0xC3,0xD4} to slave addr 0x42.
 *   2. Slave stores received bytes in slave_buf[4].
 *   3. Master READ: read 4 bytes back from slave (slave echoes slave_buf).
 *   4. Master verifies rx_buf == tx_buf.
 *
 * Clock: 16 MHz HSI, APB1 = 16 MHz.
 *   CCR = 80  (SM 100 kHz)
 *   TRISE = 17 (1000 ns rise time spec)
 *
 * Mailbox at 0x2000FC00.
 *   PASS: 4/4 bytes verified. detail0 = heartbeat counter.
 *   FAIL: error_code = step that timed out (see ERR_* constants below).
 */

#include <stdint.h>
#include "ael_mailbox.h"

/* ---- RCC ---------------------------------------------------------------- */
#define RCC_BASE            0x40023800u
#define RCC_AHB1ENR         (*(volatile uint32_t *)(RCC_BASE + 0x30u))
#define RCC_APB1ENR         (*(volatile uint32_t *)(RCC_BASE + 0x40u))
#define RCC_AHB1ENR_GPIOBEN (1u << 1)
#define RCC_APB1ENR_I2C1EN  (1u << 21)
#define RCC_APB1ENR_I2C2EN  (1u << 22)

/* ---- GPIOB -------------------------------------------------------------- */
#define GPIOB_BASE   0x40020400u
#define GPIOB_MODER  (*(volatile uint32_t *)(GPIOB_BASE + 0x00u))
#define GPIOB_OTYPER (*(volatile uint32_t *)(GPIOB_BASE + 0x04u))
#define GPIOB_PUPDR  (*(volatile uint32_t *)(GPIOB_BASE + 0x0Cu))
#define GPIOB_AFRL   (*(volatile uint32_t *)(GPIOB_BASE + 0x20u))
#define GPIOB_AFRH   (*(volatile uint32_t *)(GPIOB_BASE + 0x24u))

/* ---- I2C1 (master) — base 0x40005400 ------------------------------------ */
#define I2C1_BASE   0x40005400u
#define I2C1_CR1    (*(volatile uint32_t *)(I2C1_BASE + 0x00u))
#define I2C1_CR2    (*(volatile uint32_t *)(I2C1_BASE + 0x04u))
#define I2C1_DR     (*(volatile uint32_t *)(I2C1_BASE + 0x10u))
#define I2C1_SR1    (*(volatile uint32_t *)(I2C1_BASE + 0x14u))
#define I2C1_SR2    (*(volatile uint32_t *)(I2C1_BASE + 0x18u))
#define I2C1_CCR    (*(volatile uint32_t *)(I2C1_BASE + 0x1Cu))
#define I2C1_TRISE  (*(volatile uint32_t *)(I2C1_BASE + 0x20u))

/* ---- I2C2 (slave) — base 0x40005800 ------------------------------------- */
#define I2C2_BASE   0x40005800u
#define I2C2_CR1    (*(volatile uint32_t *)(I2C2_BASE + 0x00u))
#define I2C2_CR2    (*(volatile uint32_t *)(I2C2_BASE + 0x04u))
#define I2C2_OAR1   (*(volatile uint32_t *)(I2C2_BASE + 0x08u))
#define I2C2_DR     (*(volatile uint32_t *)(I2C2_BASE + 0x10u))
#define I2C2_SR1    (*(volatile uint32_t *)(I2C2_BASE + 0x14u))
#define I2C2_SR2    (*(volatile uint32_t *)(I2C2_BASE + 0x18u))
#define I2C2_CCR    (*(volatile uint32_t *)(I2C2_BASE + 0x1Cu))
#define I2C2_TRISE  (*(volatile uint32_t *)(I2C2_BASE + 0x20u))

/* I2C CR1 */
#define I2C_CR1_PE    (1u << 0)
#define I2C_CR1_START (1u << 8)
#define I2C_CR1_STOP  (1u << 9)
#define I2C_CR1_ACK   (1u << 10)
#define I2C_CR1_SWRST (1u << 15)

/* I2C SR1 */
#define I2C_SR1_SB    (1u << 0)
#define I2C_SR1_ADDR  (1u << 1)
#define I2C_SR1_BTF   (1u << 2)
#define I2C_SR1_STOPF (1u << 4)
#define I2C_SR1_RXNE  (1u << 6)
#define I2C_SR1_TXE   (1u << 7)
#define I2C_SR1_AF    (1u << 10)

/* I2C SR2 */
#define I2C_SR2_BUSY  (1u << 1)

/* Error codes */
#define ERR_WRITE_SB    1u
#define ERR_SWRITE_ADDR 2u
#define ERR_MWRITE_ADDR 3u
#define ERR_WRITE_DATA  4u
#define ERR_WRITE_BTF   5u
#define ERR_READ_SB     6u
#define ERR_SREAD_ADDR  7u
#define ERR_SREAD_TXE   8u
#define ERR_MREAD_ADDR  9u
#define ERR_READ_DATA   10u
#define ERR_MISMATCH    11u

/* ---- SysTick ------------------------------------------------------------ */
#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

#define N_BYTES     4u
#define I2C_TIMEOUT 200000u
#define SLAVE_ADDR  0x42u

static const uint8_t tx_buf[N_BYTES] = { 0xA1u, 0xB2u, 0xC3u, 0xD4u };
static uint8_t slave_buf[N_BYTES];
static uint8_t rx_buf[N_BYTES];

static void delay_ms(uint32_t ms)
{
    for (uint32_t i = 0u; i < ms; i++) {
        SYST_CVR = 0u;
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

static int wait_flag(volatile uint32_t *reg, uint32_t mask)
{
    uint32_t t = I2C_TIMEOUT;
    while ((*reg & mask) == 0u) {
        if (--t == 0u) return -1;
    }
    return 0;
}

int main(void)
{
    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    /* ---- Enable peripheral clocks --------------------------------------- */
    RCC_AHB1ENR |= RCC_AHB1ENR_GPIOBEN;
    (void)RCC_AHB1ENR;
    RCC_APB1ENR |= RCC_APB1ENR_I2C1EN | RCC_APB1ENR_I2C2EN;
    (void)RCC_APB1ENR;

    /* ---- GPIO: AF mode, open-drain, internal pull-up (~40 kΩ) ---------- */
    GPIOB_MODER &= ~((0x3u <<  6u) | (0x3u << 12u) |
                     (0x3u << 14u) | (0x3u << 20u));
    GPIOB_MODER |=  ((0x2u <<  6u) | (0x2u << 12u) |
                     (0x2u << 14u) | (0x2u << 20u));
    GPIOB_OTYPER |= (1u << 3u) | (1u << 6u) | (1u << 7u) | (1u << 10u);
    GPIOB_PUPDR &= ~((0x3u <<  6u) | (0x3u << 12u) |
                     (0x3u << 14u) | (0x3u << 20u));
    GPIOB_PUPDR |=  ((0x1u <<  6u) | (0x1u << 12u) |
                     (0x1u << 14u) | (0x1u << 20u));
    /* AFRL: AF9 for PB3 [15:12]; AF4 for PB6 [27:24] and PB7 [31:28] */
    GPIOB_AFRL &= ~((0xFu << 12u) | (0xFu << 24u) | (0xFu << 28u));
    GPIOB_AFRL |=  ((0x9u << 12u) | (0x4u << 24u) | (0x4u << 28u));
    /* AFRH: AF4 for PB10 [11:8] */
    GPIOB_AFRH &= ~(0xFu << 8u);
    GPIOB_AFRH |=  (0x4u << 8u);

    /* ---- I2C2 slave init ------------------------------------------------ */
    /* SWRST clears any BUSY flag latched across GDB resets (F411 errata).   */
    I2C2_CR1   = I2C_CR1_SWRST;
    delay_ms(1u);
    I2C2_CR1   = 0u;
    I2C2_CR2   = 16u;
    I2C2_CCR   = 80u;                          /* SM 100 kHz */
    I2C2_TRISE = 17u;
    I2C2_OAR1  = (SLAVE_ADDR << 1u) | (1u << 14u); /* 0x4084 */
    /* Set PE then ACK separately — simultaneous write stretches SCL on F411 */
    I2C2_CR1   = I2C_CR1_PE;
    (void)I2C2_CR1;
    I2C2_CR1  |= I2C_CR1_ACK;
    (void)I2C2_CR1;
    delay_ms(2u);

    /* ---- I2C1 master init ----------------------------------------------- */
    I2C1_CR1   = I2C_CR1_SWRST;
    delay_ms(1u);
    I2C1_CR1   = 0u;
    I2C1_CR2   = 16u;
    I2C1_CCR   = 80u;
    I2C1_TRISE = 17u;
    I2C1_CR1   = I2C_CR1_PE | I2C_CR1_ACK;

    ael_mailbox_init();

    uint32_t err     = 0u;
    uint32_t diag_sr = 0u;

    /* Sanity: I2C2 PE must still be set */
    if ((I2C2_CR1 & I2C_CR1_PE) == 0u) {
        ael_mailbox_fail(0xFDu, I2C2_CR1);
        while (1) {}
    }

    /* ==================================================================
     * WRITE PHASE: master sends tx_buf[4] to slave
     * ================================================================== */

    I2C1_CR1 |= I2C_CR1_START;
    if (wait_flag(&I2C1_SR1, I2C_SR1_SB) != 0) { err = ERR_WRITE_SB; goto fail; }

    I2C1_DR = (SLAVE_ADDR << 1u) | 0u;

    /* Wait slave ADDR */
    {
        uint32_t t = I2C_TIMEOUT;
        while ((I2C2_SR1 & I2C_SR1_ADDR) == 0u) {
            if (--t == 0u) {
                err = ERR_SWRITE_ADDR;
                diag_sr = (I2C2_SR1 & 0xFFu)
                        | ((I2C2_SR2 & 0xFFu) << 8u)
                        | ((I2C1_SR1 & 0xFFFFu) << 16u);
                goto fail;
            }
        }
    }
    (void)I2C2_SR1; (void)I2C2_SR2;

    if (wait_flag(&I2C1_SR1, I2C_SR1_ADDR) != 0) { err = ERR_MWRITE_ADDR; goto fail; }
    (void)I2C1_SR1; (void)I2C1_SR2;

    for (uint32_t i = 0u; i < N_BYTES; i++) {
        if (wait_flag(&I2C1_SR1, I2C_SR1_TXE) != 0) { err = ERR_WRITE_DATA; goto fail; }
        I2C1_DR = tx_buf[i];
        if (wait_flag(&I2C2_SR1, I2C_SR1_RXNE) != 0) { err = ERR_WRITE_DATA; goto fail; }
        slave_buf[i] = (uint8_t)I2C2_DR;
    }

    if (wait_flag(&I2C1_SR1, I2C_SR1_BTF) != 0) { err = ERR_WRITE_BTF; goto fail; }
    I2C1_CR1 |= I2C_CR1_STOP;

    {
        uint32_t t = I2C_TIMEOUT;
        while (I2C1_SR2 & I2C_SR2_BUSY) {
            if (--t == 0u) { err = ERR_WRITE_BTF; goto fail; }
        }
    }
    delay_ms(1u);

    /* ==================================================================
     * READ PHASE: master reads N_BYTES from slave
     * ================================================================== */

    I2C1_CR1 |= I2C_CR1_ACK;
    I2C1_CR1 |= I2C_CR1_START;
    if (wait_flag(&I2C1_SR1, I2C_SR1_SB) != 0) { err = ERR_READ_SB; goto fail; }

    I2C1_DR = (SLAVE_ADDR << 1u) | 1u;

    if (wait_flag(&I2C2_SR1, I2C_SR1_ADDR) != 0) { err = ERR_SREAD_ADDR; goto fail; }
    (void)I2C2_SR1; (void)I2C2_SR2;
    if (wait_flag(&I2C2_SR1, I2C_SR1_TXE) != 0) { err = ERR_SREAD_TXE; goto fail; }
    I2C2_DR = slave_buf[0];

    if (wait_flag(&I2C1_SR1, I2C_SR1_ADDR) != 0) { err = ERR_MREAD_ADDR; goto fail; }
    (void)I2C1_SR1; (void)I2C1_SR2;

    for (uint32_t i = 0u; i < 2u; i++) {
        if (wait_flag(&I2C1_SR1, I2C_SR1_RXNE) != 0) { err = ERR_READ_DATA; goto fail; }
        rx_buf[i] = (uint8_t)I2C1_DR;
        if (wait_flag(&I2C2_SR1, I2C_SR1_TXE) != 0) { err = ERR_SREAD_TXE; goto fail; }
        I2C2_DR = slave_buf[i + 1u];
    }

    if (wait_flag(&I2C2_SR1, I2C_SR1_TXE) != 0) { err = ERR_SREAD_TXE; goto fail; }
    I2C2_DR = slave_buf[3];

    if (wait_flag(&I2C1_SR1, I2C_SR1_BTF) != 0) { err = ERR_READ_DATA; goto fail; }
    I2C1_CR1 &= ~I2C_CR1_ACK;
    I2C1_CR1 |=  I2C_CR1_STOP;
    rx_buf[2] = (uint8_t)I2C1_DR;

    if (wait_flag(&I2C1_SR1, I2C_SR1_RXNE) != 0) { err = ERR_READ_DATA; goto fail; }
    rx_buf[3] = (uint8_t)I2C1_DR;

    I2C2_SR1 &= ~I2C_SR1_AF;

    /* ==================================================================
     * VERIFY
     * ================================================================== */
    {
        uint32_t matched = 0u;
        for (uint32_t i = 0u; i < N_BYTES; i++) {
            if (rx_buf[i] == tx_buf[i]) { matched++; }
        }
        if (matched != N_BYTES) {
            ael_mailbox_fail(ERR_MISMATCH, matched);
            while (1) {}
        }
    }

    ael_mailbox_pass();
    {
        uint32_t iteration = 0u;
        while (1) {
            delay_ms(1u);
            AEL_MAILBOX->detail0 = ++iteration;
        }
    }

fail:
    ael_mailbox_fail(err, diag_sr);
    while (1) {}
}
