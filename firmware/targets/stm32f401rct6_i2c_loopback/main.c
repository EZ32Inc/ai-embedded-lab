/*
 * STM32F401RCT6 — I2C1 Master / I2C2 Slave Loopback (Step 1: Internal Pull-up)
 *
 * I2C1 master: PB6 (SCL, AF4), PB7 (SDA, AF4)
 * I2C2 slave:  PB10(SCL, AF4), PB3 (SDA, AF9)
 *
 * PB3 is the alternate I2C2_SDA pin (AF9) used because PB11 (AF4) is not
 * exposed on the BlackPill connector.
 *
 * External wiring required: PB6↔PB10 (SCL bus), PB7↔PB3 (SDA bus).
 * Pull-up: STM32 internal ~40 kΩ via PUPDR=01 on all four pins.
 * (40 kΩ exceeds the I2C spec max of 10 kΩ but may work on short traces.)
 *
 * Protocol:
 *   1. Master WRITE: send tx_buf[4] = {0xA1,0xB2,0xC3,0xD4} to slave addr 0x42.
 *   2. Slave stores received bytes in slave_buf[4].
 *   3. Master READ: read 4 bytes back from slave (slave echoes slave_buf).
 *   4. Master verifies rx_buf == tx_buf.
 *
 * Clock: 16 MHz HSI, APB1 = 16 MHz.
 *   CCR = 80  (SM 100 kHz: fPCLK / (2 × fI2C) = 16e6 / 200e3 = 80)
 *   TRISE = 17 (1000 ns × 16 MHz / 1e9 + 1 = 17)
 *
 * Clock stretching (NOSTRETCH = 0 by default) holds SCL low when slave is not
 * ready, enabling single-CPU polling of both master and slave sequentially.
 *
 * 4-byte master receive sequence per RM0368 Figure 274:
 *   bytes 0–1: wait RXNE, read DR.
 *   before byte 2: wait master BTF (byte 2 in DR, byte 3 in shift reg).
 *   byte 2: clear ACK, generate STOP, read DR.
 *   byte 3: wait RXNE, read DR.
 *
 * Mailbox at 0x2000FC00.
 *   PASS: 4/4 bytes verified. detail0 = heartbeat counter.
 *   FAIL: error_code = step that timed out (see ERR_* constants below).
 *         detail0 = matched byte count (ERR_MISMATCH only; 0 for all others).
 *
 * Register addresses: RM0368 §27 (I2C), §8 (GPIO), §6 (RCC).
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
#define I2C_SR1_SB   (1u << 0)   /* start bit (master) */
#define I2C_SR1_ADDR (1u << 1)   /* address sent/matched */
#define I2C_SR1_BTF  (1u << 2)   /* byte transfer finished */
#define I2C_SR1_RXNE (1u << 6)   /* data register not empty (rx) */
#define I2C_SR1_TXE  (1u << 7)   /* data register empty (tx) */
#define I2C_SR1_AF   (1u << 10)  /* acknowledge failure */

/* I2C SR2 */
#define I2C_SR2_BUSY (1u << 1)

/* Error codes — which step timed out (single value, not bitmask) */
#define ERR_WRITE_SB    1u   /* master SB timeout, write phase */
#define ERR_SWRITE_ADDR 2u   /* slave ADDR timeout, write phase */
#define ERR_MWRITE_ADDR 3u   /* master ADDR timeout, write phase */
#define ERR_WRITE_DATA  4u   /* TXE or RXNE timeout in byte loop */
#define ERR_WRITE_BTF   5u   /* BTF/BUSY timeout after last write byte */
#define ERR_READ_SB     6u   /* master SB timeout, read phase */
#define ERR_SREAD_ADDR  7u   /* slave ADDR timeout, read phase */
#define ERR_SREAD_TXE   8u   /* slave TXE timeout, read phase */
#define ERR_MREAD_ADDR  9u   /* master ADDR timeout, read phase */
#define ERR_READ_DATA   10u  /* RXNE or BTF timeout, read phase */
#define ERR_MISMATCH    11u  /* rx_buf != tx_buf; detail0 = matched count */

/* ---- SysTick ------------------------------------------------------------ */
#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

#define N_BYTES     4u
#define I2C_TIMEOUT 200000u    /* ~2 ms at 16 MHz, covers a full byte at 100 kHz */
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

/* Poll register bit(s) until set; returns 0 on success, -1 on timeout. */
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
    (void)RCC_AHB1ENR;                         /* AHB read-back for clock propagation */
    RCC_APB1ENR |= RCC_APB1ENR_I2C1EN | RCC_APB1ENR_I2C2EN;
    (void)RCC_APB1ENR;

    /* ---- GPIO: open-drain, internal pull-up (~40 kΩ) -------------------- */
    /*
     * PB3  I2C2_SDA: MODER[7:6]=10,   OTYPER[3]=1,  PUPDR[7:6]=01,   AFRL[15:12]=9 (AF9)
     * PB6  I2C1_SCL: MODER[13:12]=10, OTYPER[6]=1,  PUPDR[13:12]=01, AFRL[27:24]=4 (AF4)
     * PB7  I2C1_SDA: MODER[15:14]=10, OTYPER[7]=1,  PUPDR[15:14]=01, AFRL[31:28]=4 (AF4)
     * PB10 I2C2_SCL: MODER[21:20]=10, OTYPER[10]=1, PUPDR[21:20]=01, AFRH[11:8]=4  (AF4)
     */
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

    /* ---- I2C2 slave init (must be ready before master generates START) -- */
    /*
     * Software-reset before configuring: clears any stale state left by a
     * previous run (the STM32 I2C peripheral can latch BUSY across GDB resets).
     * OAR1 bit 14 must remain 1 (reserved, RM0368 §27.6.3).
     * ACK=1: slave hardware auto-acks matching addresses and data bytes.
     * NOSTRETCH=0 (default): slave stretches SCL when not ready, required
     * for single-CPU polling interleaving.
     */
    I2C2_CR1   = I2C_CR1_SWRST;               /* assert software reset */
    delay_ms(1u);
    I2C2_CR1   = 0u;                           /* release reset, PE=0 */
    I2C2_CR2   = 16u;                          /* FREQ = 16 MHz */
    I2C2_CCR   = 80u;                          /* SM 100 kHz */
    I2C2_TRISE = 17u;
    I2C2_OAR1  = (SLAVE_ADDR << 1u) | (1u << 14u); /* 7-bit addr 0x42 */
    I2C2_CR1   = I2C_CR1_PE | I2C_CR1_ACK;

    delay_ms(2u);                              /* let slave stabilise on bus */

    /* ---- I2C1 master init ----------------------------------------------- */
    I2C1_CR1   = I2C_CR1_SWRST;
    delay_ms(1u);
    I2C1_CR1   = 0u;
    I2C1_CR2   = 16u;
    I2C1_CCR   = 80u;
    I2C1_TRISE = 17u;
    I2C1_CR1   = I2C_CR1_PE | I2C_CR1_ACK;

    ael_mailbox_init();

    /*
     * Capture BUSY state at startup for diagnostics.
     * detail0=1 on FAIL means BUSY was stuck when START was attempted;
     * detail0=0 means the bus appeared idle but SB still did not set.
     */
    uint32_t err      = 0u;
    uint32_t i2c_diag = (I2C1_SR2 & I2C_SR2_BUSY) ? 1u : 0u;

    /* ==================================================================
     * WRITE PHASE: master sends tx_buf[4] to slave (slave stores in slave_buf)
     * ==================================================================
     *
     * Slave hardware stretches SCL after each address/data byte until
     * the slave state machine clears the corresponding flag (ADDR, RXNE).
     * Slave state must be serviced FIRST so SCL is released before we
     * poll the master's corresponding flag.
     */

    /* Generate START condition */
    I2C1_CR1 |= I2C_CR1_START;
    if (wait_flag(&I2C1_SR1, I2C_SR1_SB) != 0) { err = ERR_WRITE_SB; goto fail; }

    /* Send slave address + write bit; slave auto-acks when OAR1 matches */
    I2C1_DR = (SLAVE_ADDR << 1u) | 0u;

    /* Slave: address matched → ADDR set, SCL stretched; read SR1+SR2 to clear */
    if (wait_flag(&I2C2_SR1, I2C_SR1_ADDR) != 0) { err = ERR_SWRITE_ADDR; goto fail; }
    (void)I2C2_SR1; (void)I2C2_SR2;           /* clears slave ADDR, releases SCL */

    /* Master: address ACKed → ADDR set; clear to enter data phase */
    if (wait_flag(&I2C1_SR1, I2C_SR1_ADDR) != 0) { err = ERR_MWRITE_ADDR; goto fail; }
    (void)I2C1_SR1; (void)I2C1_SR2;           /* clears master ADDR; TXE already set */

    /* Transfer N_BYTES bytes */
    for (uint32_t i = 0u; i < N_BYTES; i++) {
        /* Master: wait shift register empty, write next byte */
        if (wait_flag(&I2C1_SR1, I2C_SR1_TXE) != 0) { err = ERR_WRITE_DATA; goto fail; }
        I2C1_DR = tx_buf[i];
        /* Slave: wait byte received, store in slave_buf */
        if (wait_flag(&I2C2_SR1, I2C_SR1_RXNE) != 0) { err = ERR_WRITE_DATA; goto fail; }
        slave_buf[i] = (uint8_t)I2C2_DR;
    }

    /*
     * Wait BTF: last byte fully transmitted (shift register empty, DR not refilled).
     * BTF includes the ACK clock cycle, so it is safe to generate STOP after.
     */
    if (wait_flag(&I2C1_SR1, I2C_SR1_BTF) != 0) { err = ERR_WRITE_BTF; goto fail; }
    I2C1_CR1 |= I2C_CR1_STOP;

    /* Wait for bus to be free (BUSY clears after STOP) */
    {
        uint32_t t = I2C_TIMEOUT;
        while (I2C1_SR2 & I2C_SR2_BUSY) {
            if (--t == 0u) { err = ERR_WRITE_BTF; goto fail; }
        }
    }
    delay_ms(1u);   /* guard time before next START */

    /* ==================================================================
     * READ PHASE: master reads N_BYTES from slave (slave echoes slave_buf)
     * ==================================================================
     *
     * 4-byte master receive per RM0368 Figure 274:
     *   After clearing master ADDR:
     *     byte 0: RXNE → read DR                (ACK sent automatically)
     *     byte 1: RXNE → read DR                (ACK sent automatically)
     *     byte 2: BTF (byte 2 in DR, byte 3 in shift) →
     *               clear ACK, STOP, read DR
     *     byte 3: RXNE → read DR
     *
     * Slave side: load each byte into DR when TXE set (previous byte
     * moved to shift register). SCL stretching prevents overrun.
     */

    I2C1_CR1 |= I2C_CR1_ACK;          /* re-enable ACK for multi-byte receive */

    /* Generate START */
    I2C1_CR1 |= I2C_CR1_START;
    if (wait_flag(&I2C1_SR1, I2C_SR1_SB) != 0) { err = ERR_READ_SB; goto fail; }

    /* Send slave address + read bit */
    I2C1_DR = (SLAVE_ADDR << 1u) | 1u;

    /*
     * Slave: ADDR set in transmitter mode; TXE is also set simultaneously.
     * Clear ADDR first, then load slave_buf[0] into slave DR.
     * SCL is stretched until both operations complete.
     */
    if (wait_flag(&I2C2_SR1, I2C_SR1_ADDR) != 0) { err = ERR_SREAD_ADDR; goto fail; }
    (void)I2C2_SR1; (void)I2C2_SR2;           /* clears slave ADDR */
    if (wait_flag(&I2C2_SR1, I2C_SR1_TXE) != 0) { err = ERR_SREAD_TXE; goto fail; }
    I2C2_DR = slave_buf[0];                    /* byte 0 ready for clocking */

    /* Master: clear ADDR → master begins clocking byte 0 */
    if (wait_flag(&I2C1_SR1, I2C_SR1_ADDR) != 0) { err = ERR_MREAD_ADDR; goto fail; }
    (void)I2C1_SR1; (void)I2C1_SR2;

    /*
     * Bytes 0 and 1: read from master DR, then load next slave byte.
     * Slave TXE sets when current byte moves from DR to shift register
     * (before the byte is fully clocked), so load of next byte is timely.
     */
    for (uint32_t i = 0u; i < 2u; i++) {
        if (wait_flag(&I2C1_SR1, I2C_SR1_RXNE) != 0) { err = ERR_READ_DATA; goto fail; }
        rx_buf[i] = (uint8_t)I2C1_DR;
        if (wait_flag(&I2C2_SR1, I2C_SR1_TXE) != 0) { err = ERR_SREAD_TXE; goto fail; }
        I2C2_DR = slave_buf[i + 1u];
    }
    /* slave DR now has slave_buf[2]; rx_buf[0..1] are filled */

    /*
     * Load slave_buf[3] after slave_buf[2] moves to shift register (TXE).
     * Then wait master BTF: byte 2 in master DR + byte 3 in master shift reg.
     */
    if (wait_flag(&I2C2_SR1, I2C_SR1_TXE) != 0) { err = ERR_SREAD_TXE; goto fail; }
    I2C2_DR = slave_buf[3];

    if (wait_flag(&I2C1_SR1, I2C_SR1_BTF) != 0) { err = ERR_READ_DATA; goto fail; }
    I2C1_CR1 &= ~I2C_CR1_ACK;         /* NACK will be sent after byte 3 */
    I2C1_CR1 |=  I2C_CR1_STOP;        /* STOP after byte 3 */
    rx_buf[2] = (uint8_t)I2C1_DR;     /* byte 2 from DR; byte 3 moves shift→DR */

    if (wait_flag(&I2C1_SR1, I2C_SR1_RXNE) != 0) { err = ERR_READ_DATA; goto fail; }
    rx_buf[3] = (uint8_t)I2C1_DR;

    /* Clear slave AF: set by hardware when master sends NACK after last byte */
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
    ael_mailbox_fail(err, i2c_diag);
    while (1) {}
}
