/*
 * STM32H750VBT6 — Step 1 Wiring Verify
 *
 * Tests bench loopback wiring via on-chip firmware. No LA required.
 * Result read via SWD mailbox at SRAM4 (0x38000000).
 *
 * Tests performed:
 *   [bit 0] ERR_GPIO_HIGH : PB8=H → PB9 read != H
 *   [bit 1] ERR_GPIO_LOW  : PB8=L → PB9 read != L
 *   [bit 2] ERR_UART      : PA9(TX)→PA10(RX) 0x5A loopback timeout/mismatch
 *
 * ADC/DAC (PA4→PA0) is NOT tested here — requires ADC kernel clock
 * configuration (RCC_CDCCIPR). Covered in stm32h750_adc_read.
 *
 * All register addresses from RM0433 (STM32H750 Reference Manual).
 * Step 0 clock/cache rules remain in force: no PLL, no cache, no MPU.
 */

#define AEL_MAILBOX_ADDR  0x38000000u
#include "../ael_mailbox.h"

/* ---- RCC (RM0433 §8) ---------------------------------------------------- */

#define RCC_BASE              0x58024400u
#define RCC_AHB4ENR           (*(volatile uint32_t *)(RCC_BASE + 0x0E0u))
#define RCC_APB2ENR           (*(volatile uint32_t *)(RCC_BASE + 0x0F0u))

#define RCC_AHB4ENR_GPIOAEN   (1u << 0)
#define RCC_AHB4ENR_GPIOBEN   (1u << 1)
#define RCC_APB2ENR_USART1EN  (1u << 4)

/* ---- GPIOA (RM0433 §10, base 0x58020000) -------------------------------- */

#define GPIOA_BASE   0x58020000u
#define GPIOA_MODER  (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_AFRH   (*(volatile uint32_t *)(GPIOA_BASE + 0x24u))

/* ---- GPIOB (RM0433 §10, base 0x58020400) -------------------------------- */

#define GPIOB_BASE   0x58020400u
#define GPIOB_MODER  (*(volatile uint32_t *)(GPIOB_BASE + 0x00u))
#define GPIOB_IDR    (*(volatile uint32_t *)(GPIOB_BASE + 0x10u))
#define GPIOB_ODR    (*(volatile uint32_t *)(GPIOB_BASE + 0x14u))

/* ---- SysTick (ARMv7-M ARM) ---------------------------------------------- */

#define SYST_CSR       (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR       (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR       (*(volatile uint32_t *)0xE000E018u)

#define SYST_CSR_ENABLE     (1u << 0)
#define SYST_CSR_CLKSOURCE  (1u << 2)
#define SYST_CSR_COUNTFLAG  (1u << 16)

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

/* ---- Error bitmask written to mailbox.error_code ------------------------ */

#define ERR_GPIO_HIGH   (1u << 0)
#define ERR_GPIO_LOW    (1u << 1)
#define ERR_UART        (1u << 2)

/* ---- Delay -------------------------------------------------------------- */

static void delay_ticks(uint32_t ticks)
{
    for (volatile uint32_t i = 0u; i < ticks; i++) {
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

/* ---- GPIO loopback: PB8 (output) → PB9 (input) ------------------------- */

static uint32_t test_gpio_loopback(void)
{
    uint32_t err = 0u;

    /* PB8: output push-pull (MODER bits [17:16] = 01) */
    GPIOB_MODER &= ~(0x3u << 16u);
    GPIOB_MODER |=  (0x1u << 16u);

    /* PB9: input floating (MODER bits [19:18] = 00) */
    GPIOB_MODER &= ~(0x3u << 18u);

    /* Drive high, wait 2 ms, read PB9 */
    GPIOB_ODR |= (1u << 8u);
    delay_ticks(2u);
    if ((GPIOB_IDR & (1u << 9u)) == 0u) {
        err |= ERR_GPIO_HIGH;
    }

    /* Drive low, wait 2 ms, read PB9 */
    GPIOB_ODR &= ~(1u << 8u);
    delay_ticks(2u);
    if ((GPIOB_IDR & (1u << 9u)) != 0u) {
        err |= ERR_GPIO_LOW;
    }

    return err;
}

/* ---- UART loopback: PA9 (USART1_TX) → PA10 (USART1_RX) ----------------- */

static uint32_t test_uart_loopback(void)
{
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

    /* Enable USART1 clock, read-back to ensure active */
    RCC_APB2ENR |= RCC_APB2ENR_USART1EN;
    (void)RCC_APB2ENR;

    /* 115200 baud from 64 MHz APB2: BRR = 64000000 / 115200 = 556 */
    USART1_CR1 = 0u;       /* disable before configure */
    USART1_BRR = 556u;
    USART1_CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;

    /* Wait for TXE, send 0x5A */
    uint32_t timeout = 1000000u;
    while ((USART1_ISR & USART_ISR_TXE) == 0u) {
        if (--timeout == 0u) { return ERR_UART; }
    }
    USART1_TDR = 0x5Au;

    /* Wait for RXNE, read and compare */
    timeout = 1000000u;
    while ((USART1_ISR & USART_ISR_RXNE) == 0u) {
        if (--timeout == 0u) { return ERR_UART; }
    }
    if ((uint8_t)USART1_RDR != 0x5Au) {
        return ERR_UART;
    }

    return 0u;
}

/* ---- Main --------------------------------------------------------------- */

int main(void)
{
    /* SysTick: processor clock (64 MHz HSI), RVR=63999 → 1 ms/tick */
    SYST_RVR = 63999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    /* Enable GPIOA and GPIOB clocks */
    RCC_AHB4ENR |= RCC_AHB4ENR_GPIOAEN | RCC_AHB4ENR_GPIOBEN;
    (void)RCC_AHB4ENR;

    ael_mailbox_init();

    uint32_t err = 0u;
    err |= test_gpio_loopback();
    err |= test_uart_loopback();

    if (err == 0u) {
        ael_mailbox_pass();
        /*
         * PASS: increment detail0 each tick — two consecutive GDB reads
         * with increasing values prove the MCU is still running.
         */
        uint32_t iteration = 0u;
        while (1) {
            delay_ticks(1u);
            iteration++;
            AEL_MAILBOX->detail0 = iteration;
        }
    } else {
        /*
         * FAIL: error_code bitmask tells which wires failed.
         * detail0 stays frozen — confirms MCU halted in fail branch.
         *   bit 0: ERR_GPIO_HIGH  (PB8=H → PB9 read != H)
         *   bit 1: ERR_GPIO_LOW   (PB8=L → PB9 read != L)
         *   bit 2: ERR_UART       (PA9→PA10 byte mismatch/timeout)
         */
        ael_mailbox_fail(err, 0u);
        while (1) {}
    }
}
