/*
 * STM32F401RCT6 — USART1 + DMA2 Loopback Test
 *
 * PA9 (USART1_TX, AF7) → PA10 (USART1_RX, AF7), hardware loopback.
 * Transmits 8 bytes via DMA2 Stream7 Ch4 (USART1_TX).
 * Receives  8 bytes via DMA2 Stream2 Ch4 (USART1_RX).
 * Verifies TX buffer == RX buffer.
 *
 * Clock: 16 MHz HSI. BRR=139 → 115200 baud.
 * DMA2: AHB1 peripheral, clock enabled via RCC_AHB1ENR bit 22.
 *
 * Mailbox at 0x2000FC00.
 *   PASS: all 8 bytes match. detail0 = heartbeat counter.
 *   FAIL: error_code bit0=ERR_RX_TIMEOUT, bit1=ERR_DATA_MISMATCH.
 *         detail0 = number of matched bytes (0–7).
 *
 * Register addresses: RM0368 (STM32F401 Reference Manual).
 */

#include <stdint.h>
#include "ael_mailbox.h"

/* ---- RCC ---------------------------------------------------------------- */
#define RCC_BASE           0x40023800u
#define RCC_AHB1ENR        (*(volatile uint32_t *)(RCC_BASE + 0x30u))
#define RCC_APB2ENR        (*(volatile uint32_t *)(RCC_BASE + 0x44u))
#define RCC_AHB1ENR_GPIOAEN  (1u << 0)
#define RCC_AHB1ENR_DMA2EN   (1u << 22)
#define RCC_APB2ENR_USART1EN (1u << 4)

/* ---- GPIOA -------------------------------------------------------------- */
#define GPIOA_BASE  0x40020000u
#define GPIOA_MODER (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_AFRH  (*(volatile uint32_t *)(GPIOA_BASE + 0x24u))

/* ---- USART1 ------------------------------------------------------------- */
#define USART1_BASE  0x40011000u
#define USART1_SR    (*(volatile uint32_t *)(USART1_BASE + 0x00u))
#define USART1_DR    (*(volatile uint32_t *)(USART1_BASE + 0x04u))
#define USART1_BRR   (*(volatile uint32_t *)(USART1_BASE + 0x08u))
#define USART1_CR1   (*(volatile uint32_t *)(USART1_BASE + 0x0Cu))
#define USART1_CR3   (*(volatile uint32_t *)(USART1_BASE + 0x14u))
#define USART_CR1_RE   (1u << 2)
#define USART_CR1_TE   (1u << 3)
#define USART_CR1_UE   (1u << 13)
#define USART_CR3_DMAR (1u << 6)
#define USART_CR3_DMAT (1u << 7)
#define USART_SR_TC    (1u << 6)

/* ---- DMA2 --------------------------------------------------------------- */
/*
 * DMA2 base: 0x40026400
 * Stream n base: DMA2_BASE + 0x10 + n*0x18
 *   Stream 2 (USART1_RX, Ch4): base + 0x40
 *   Stream 7 (USART1_TX, Ch4): base + 0xB8
 * Per-stream registers: CR(+0), NDTR(+4), PAR(+8), M0AR(+C), M1AR(+10), FCR(+14)
 *
 * LISR (streams 0-3): stream 2 flags at bits [21:16]
 * HISR (streams 4-7): stream 7 flags at bits [27:22]
 * Flag bit positions within the 6-bit group: FEIF=0,DMEIF=2,TEIF=3,HTIF=4,TCIF=5
 */
#define DMA2_BASE   0x40026400u
#define DMA2_LISR   (*(volatile uint32_t *)(DMA2_BASE + 0x00u))
#define DMA2_HISR   (*(volatile uint32_t *)(DMA2_BASE + 0x04u))
#define DMA2_LIFCR  (*(volatile uint32_t *)(DMA2_BASE + 0x08u))
#define DMA2_HIFCR  (*(volatile uint32_t *)(DMA2_BASE + 0x0Cu))

/* Stream 2 (RX) */
#define DMA2_S2CR   (*(volatile uint32_t *)(DMA2_BASE + 0x40u))
#define DMA2_S2NDTR (*(volatile uint32_t *)(DMA2_BASE + 0x44u))
#define DMA2_S2PAR  (*(volatile uint32_t *)(DMA2_BASE + 0x48u))
#define DMA2_S2M0AR (*(volatile uint32_t *)(DMA2_BASE + 0x4Cu))

/* Stream 7 (TX) */
#define DMA2_S7CR   (*(volatile uint32_t *)(DMA2_BASE + 0xB8u))
#define DMA2_S7NDTR (*(volatile uint32_t *)(DMA2_BASE + 0xBCu))
#define DMA2_S7PAR  (*(volatile uint32_t *)(DMA2_BASE + 0xC0u))
#define DMA2_S7M0AR (*(volatile uint32_t *)(DMA2_BASE + 0xC4u))

/* DMA CR bits */
#define DMA_CR_EN     (1u << 0)
#define DMA_CR_MINC   (1u << 10)
#define DMA_CR_DIR_M2P (1u << 6)   /* memory-to-peripheral */
#define DMA_CR_CHSEL4 (4u << 25)   /* channel 4 */

/* Flags for stream 2 in LISR/LIFCR (base offset = 16) */
#define DMA2_LISR_TCIF2  (1u << 21)
#define DMA2_LISR_TEIF2  (1u << 19)
#define DMA2_LIFCR_CTCIF2 (1u << 21)
#define DMA2_LIFCR_CTEIF2 (1u << 19)
#define DMA2_LIFCR_ALL2  (0x3Fu << 16)

/* Flags for stream 7 in HISR/HIFCR (base offset = 22) */
#define DMA2_HISR_TCIF7  (1u << 27)
#define DMA2_HISR_TEIF7  (1u << 25)
#define DMA2_HIFCR_CTCIF7 (1u << 27)
#define DMA2_HIFCR_ALL7  (0x3Fu << 22)

/* ---- SysTick ------------------------------------------------------------ */
#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

#define ERR_RX_TIMEOUT     (1u << 0)
#define ERR_DATA_MISMATCH  (1u << 1)

#define N_BYTES   8u
#define DMA_TIMEOUT 2000000u

static const uint8_t tx_buf[N_BYTES] = {
    0xA1u, 0xB2u, 0xC3u, 0xD4u, 0xE5u, 0xF6u, 0x12u, 0x34u
};
static uint8_t rx_buf[N_BYTES];

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

    /* Enable clocks: GPIOA, DMA2, USART1 */
    RCC_AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_DMA2EN;
    (void)RCC_AHB1ENR;
    RCC_APB2ENR |= RCC_APB2ENR_USART1EN;
    (void)RCC_APB2ENR;

    /* PA9 → AF7 (USART1_TX): MODER[19:18]=10, AFRH[7:4]=7 */
    GPIOA_MODER &= ~(0x3u << 18u);
    GPIOA_MODER |=  (0x2u << 18u);
    GPIOA_AFRH  &= ~(0xFu <<  4u);
    GPIOA_AFRH  |=  (0x7u <<  4u);

    /* PA10 → AF7 (USART1_RX): MODER[21:20]=10, AFRH[11:8]=7 */
    GPIOA_MODER &= ~(0x3u << 20u);
    GPIOA_MODER |=  (0x2u << 20u);
    GPIOA_AFRH  &= ~(0xFu <<  8u);
    GPIOA_AFRH  |=  (0x7u <<  8u);

    /* USART1: 115200 baud, 8N1, DMA enabled for TX and RX */
    USART1_CR1 = 0u;
    USART1_BRR = 139u;
    USART1_CR3 = USART_CR3_DMAT | USART_CR3_DMAR;
    USART1_CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;

    /*
     * DMA2 Stream2 — USART1_RX, peripheral→memory, Ch4.
     * Set up RX first so it is ready before TX fires.
     */
    DMA2_S2CR = 0u;                          /* disable stream */
    while (DMA2_S2CR & DMA_CR_EN) {}         /* wait for disable */
    DMA2_LIFCR = DMA2_LIFCR_ALL2;           /* clear all flags */
    DMA2_S2PAR  = (uint32_t)&USART1_DR;
    DMA2_S2M0AR = (uint32_t)rx_buf;
    DMA2_S2NDTR = N_BYTES;
    DMA2_S2CR   = DMA_CR_CHSEL4 | DMA_CR_MINC; /* P→M, ch4, minc */
    DMA2_S2CR  |= DMA_CR_EN;

    /*
     * DMA2 Stream7 — USART1_TX, memory→peripheral, Ch4.
     */
    DMA2_S7CR = 0u;
    while (DMA2_S7CR & DMA_CR_EN) {}
    DMA2_HIFCR = DMA2_HIFCR_ALL7;
    DMA2_S7PAR  = (uint32_t)&USART1_DR;
    DMA2_S7M0AR = (uint32_t)tx_buf;
    DMA2_S7NDTR = N_BYTES;
    DMA2_S7CR   = DMA_CR_CHSEL4 | DMA_CR_MINC | DMA_CR_DIR_M2P; /* M→P, ch4, minc */
    DMA2_S7CR  |= DMA_CR_EN;

    ael_mailbox_init();

    /* Wait for RX DMA transfer complete */
    uint32_t timeout = DMA_TIMEOUT;
    while ((DMA2_LISR & DMA2_LISR_TCIF2) == 0u) {
        if (--timeout == 0u) {
            ael_mailbox_fail(ERR_RX_TIMEOUT, 0u);
            while (1) {}
        }
    }
    DMA2_LIFCR = DMA2_LIFCR_CTCIF2;

    /* Verify data */
    uint32_t matched = 0u;
    for (uint32_t i = 0u; i < N_BYTES; i++) {
        if (rx_buf[i] == tx_buf[i]) { matched++; }
    }

    if (matched == N_BYTES) {
        ael_mailbox_pass();
        uint32_t iteration = 0u;
        while (1) {
            delay_ms(1u);
            AEL_MAILBOX->detail0 = ++iteration;
        }
    } else {
        ael_mailbox_fail(ERR_DATA_MISMATCH, matched);
        while (1) {}
    }
}
