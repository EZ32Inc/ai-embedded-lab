#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x20004C00u
#include "../ael_mailbox.h"

#define RCC_BASE 0x40021000
#define RCC_APB2ENR (*(volatile uint32_t *)(RCC_BASE + 0x18))

#define GPIOA_BASE 0x40010800
#define GPIOA_CRL (*(volatile uint32_t *)(GPIOA_BASE + 0x00))
#define GPIOA_CRH (*(volatile uint32_t *)(GPIOA_BASE + 0x04))
#define GPIOA_ODR (*(volatile uint32_t *)(GPIOA_BASE + 0x0C))

#define GPIOC_BASE 0x40011000
#define GPIOC_CRH (*(volatile uint32_t *)(GPIOC_BASE + 0x04))
#define GPIOC_ODR (*(volatile uint32_t *)(GPIOC_BASE + 0x0C))

#define SPI1_BASE 0x40013000
#define SPI1_CR1 (*(volatile uint32_t *)(SPI1_BASE + 0x00))
#define SPI1_SR (*(volatile uint32_t *)(SPI1_BASE + 0x08))
#define SPI1_DR (*(volatile uint32_t *)(SPI1_BASE + 0x0C))

#define SYSTICK_BASE 0xE000E010u
#define SYST_CSR (*(volatile uint32_t *)(SYSTICK_BASE + 0x00u))
#define SYST_RVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x04u))
#define SYST_CVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x08u))

#define RCC_IOPAEN (1u << 2)
#define RCC_IOPCEN (1u << 4)
#define RCC_SPI1EN (1u << 12)
#define SPI_CR1_MSTR (1u << 2)
#define SPI_CR1_BR_DIV16 (0x3u << 3)
#define SPI_CR1_SSI (1u << 8)
#define SPI_CR1_SSM (1u << 9)
#define SPI_CR1_SPE (1u << 6)
#define SPI_SR_RXNE (1u << 0)
#define SPI_SR_TXE (1u << 1)
#define SPI_SR_BSY (1u << 7)
#define SYST_CSR_ENABLE (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

static void delay_cycles(volatile uint32_t n) {
    while (n-- > 0u) {
        __asm__ volatile ("nop");
    }
}

static void spi1_init(void) {
    GPIOA_CRL &= ~(0xFFFu << 20);
    GPIOA_CRL |= (0xB4Bu << 20); /* PA5/PA7 AF PP, PA6 input floating */
    SPI1_CR1 = SPI_CR1_MSTR | SPI_CR1_BR_DIV16 | SPI_CR1_SSI | SPI_CR1_SSM | SPI_CR1_SPE;
}

static uint8_t spi1_transfer(uint8_t value, uint8_t *out) {
    while ((SPI1_SR & SPI_SR_RXNE) != 0u) {
        (void)SPI1_DR;
    }
    while ((SPI1_SR & SPI_SR_TXE) == 0u) {
    }
    SPI1_DR = value;
    for (uint32_t i = 0; i < 100000u; ++i) {
        if ((SPI1_SR & SPI_SR_RXNE) != 0u) {
            *out = (uint8_t)(SPI1_DR & 0xFFu);
            while ((SPI1_SR & SPI_SR_BSY) != 0u) {
            }
            return 1u;
        }
    }
    while ((SPI1_SR & SPI_SR_BSY) != 0u) {
    }
    return 0u;
}

int main(void) {
    const uint8_t patterns[] = {0x55u, 0xA5u, 0x3Cu, 0xC3u};
    uint32_t led_ticks = 0u;

    RCC_APB2ENR |= (RCC_IOPAEN | RCC_IOPCEN | RCC_SPI1EN);

    GPIOA_CRL &= ~(0xFu << 16);
    GPIOA_CRL |= (0x3u << 16); /* PA4 as GPIO output; PA5..PA7 configured by SPI init */
    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x2u << 20);
    GPIOC_ODR |= (1u << 13);

    spi1_init();
    ael_mailbox_init();

    for (uint32_t i = 0; i < (sizeof(patterns) / sizeof(patterns[0])); ++i) {
        uint8_t rx = 0u;
        uint8_t expected = patterns[i];
        uint8_t ok = spi1_transfer(expected, &rx);
        if (ok == 0u || rx != expected) {
            ael_mailbox_fail(0x5001u, ((uint32_t)expected << 8) | rx);
            while (1) {
            }
        }
        delay_cycles(12000u);
    }

    ael_mailbox_pass();
    GPIOA_ODR |= (1u << 4);

    while (1) {
        led_ticks += 1u;
        if (led_ticks >= 100000u) {
            led_ticks = 0u;
            GPIOC_ODR ^= (1u << 13);
        }
        AEL_MAILBOX->detail0 += 1u;
    }
}
