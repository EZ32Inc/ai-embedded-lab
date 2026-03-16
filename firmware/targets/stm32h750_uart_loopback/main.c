/*
 * STM32H750VBT6 — UART Loopback Test
 *
 * Tests PA9 (USART1_TX, AF7) → PA10 (USART1_RX, AF7) loopback.
 * Sends 4-byte sequence {0x55, 0xAA, 0x12, 0x34}, verifies each byte.
 *
 * Error bits in error_code:
 *   bit 0: byte 0 (0x55) mismatch or timeout
 *   bit 1: byte 1 (0xAA) mismatch or timeout
 *   bit 2: byte 2 (0x12) mismatch or timeout
 *   bit 3: byte 3 (0x34) mismatch or timeout
 *
 * detail0 on PASS = 4 (matched bytes), then increments each ms tick.
 *
 * All register addresses from RM0433 (STM32H750 Reference Manual).
 */

#define AEL_MAILBOX_ADDR  0x38000000u
#include "../ael_mailbox.h"

/* ---- RCC (RM0433 §8) ---------------------------------------------------- */

#define RCC_BASE              0x58024400u
#define RCC_AHB4ENR           (*(volatile uint32_t *)(RCC_BASE + 0x0E0u))
#define RCC_APB2ENR           (*(volatile uint32_t *)(RCC_BASE + 0x0F0u))
#define RCC_AHB4ENR_GPIOAEN   (1u << 0)
#define RCC_APB2ENR_USART1EN  (1u << 4)

/* ---- GPIOA (RM0433 §10, base 0x58020000) -------------------------------- */

#define GPIOA_BASE   0x58020000u
#define GPIOA_MODER  (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_AFRH   (*(volatile uint32_t *)(GPIOA_BASE + 0x24u))

/* ---- USART1 (RM0433 §53, APB2 base 0x40011000) -------------------------- */

#define USART1_BASE  0x40011000u
#define USART1_CR1   (*(volatile uint32_t *)(USART1_BASE + 0x00u))
#define USART1_BRR   (*(volatile uint32_t *)(USART1_BASE + 0x0Cu))
#define USART1_ISR   (*(volatile uint32_t *)(USART1_BASE + 0x1Cu))
#define USART1_RDR   (*(volatile uint32_t *)(USART1_BASE + 0x24u))
#define USART1_TDR   (*(volatile uint32_t *)(USART1_BASE + 0x28u))

#define USART_CR1_UE   (1u << 0)
#define USART_CR1_RE   (1u << 2)
#define USART_CR1_TE   (1u << 3)
#define USART_ISR_RXNE (1u << 5)
#define USART_ISR_TXE  (1u << 7)

/* ---- SysTick (ARMv7-M ARM) ---------------------------------------------- */

#define SYST_CSR        (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR        (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR        (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

/* ---- Helpers ------------------------------------------------------------ */

static void delay_ticks(uint32_t ticks)
{
    for (volatile uint32_t i = 0u; i < ticks; i++) {
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

/* ---- Main --------------------------------------------------------------- */

int main(void)
{
    /* SysTick: processor clock (64 MHz HSI), RVR=63999 → 1 ms/tick */
    SYST_RVR = 63999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    /* Enable GPIOA and USART1 clocks */
    RCC_AHB4ENR |= RCC_AHB4ENR_GPIOAEN;
    (void)RCC_AHB4ENR;
    RCC_APB2ENR |= RCC_APB2ENR_USART1EN;
    (void)RCC_APB2ENR;

    ael_mailbox_init();

    /* PA9 → AF7 (USART1_TX): MODER[19:18]=10, AFRH[7:4]=7 */
    GPIOA_MODER &= ~(0x3u << 18u);
    GPIOA_MODER |=  (0x2u << 18u);
    GPIOA_AFRH  &= ~(0xFu << 4u);
    GPIOA_AFRH  |=  (0x7u << 4u);

    /* PA10 → AF7 (USART1_RX): MODER[21:20]=10, AFRH[11:8]=7 */
    GPIOA_MODER &= ~(0x3u << 20u);
    GPIOA_MODER |=  (0x2u << 20u);
    GPIOA_AFRH  &= ~(0xFu << 8u);
    GPIOA_AFRH  |=  (0x7u << 8u);

    /* Configure USART1: 115200 baud from 64 MHz APB2 (BRR=556), 8N1 */
    USART1_CR1 = 0u;
    USART1_BRR = 556u;
    USART1_CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;

    /* Test sequence */
    static const uint8_t seq[4] = { 0x55u, 0xAAu, 0x12u, 0x34u };
    uint32_t err     = 0u;
    uint32_t matched = 0u;

    for (uint32_t i = 0u; i < 4u; i++) {
        uint32_t timeout;

        /* Wait TXE, send byte */
        timeout = 1000000u;
        while ((USART1_ISR & USART_ISR_TXE) == 0u) {
            if (--timeout == 0u) { err |= (1u << i); goto next; }
        }
        USART1_TDR = seq[i];

        /* Wait RXNE, read byte */
        timeout = 1000000u;
        while ((USART1_ISR & USART_ISR_RXNE) == 0u) {
            if (--timeout == 0u) { err |= (1u << i); goto next; }
        }
        if ((uint8_t)USART1_RDR == seq[i]) {
            matched++;
        } else {
            err |= (1u << i);
        }

    next:
        (void)0;
    }

    if (err == 0u) {
        ael_mailbox_pass();
        /* PASS: detail0 = 4 (matched count), increments each ms */
        uint32_t iteration = matched;   /* == 4 */
        while (1) {
            delay_ticks(1u);
            iteration++;
            AEL_MAILBOX->detail0 = iteration;
        }
    } else {
        ael_mailbox_fail(err, matched);
        while (1) {}
    }
}
