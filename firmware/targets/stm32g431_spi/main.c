#include <stdint.h>
#include "../ael_mailbox.h"

/* STM32G431 — GPIO on AHB2 */
#define RCC_BASE       0x40021000u
#define RCC_AHB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x4Cu))
#define RCC_APB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x60u))

#define GPIOA_BASE     0x48000000u
#define GPIOA_MODER    (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_OTYPER   (*(volatile uint32_t *)(GPIOA_BASE + 0x04u))
#define GPIOA_OSPEEDR  (*(volatile uint32_t *)(GPIOA_BASE + 0x08u))
#define GPIOA_ODR      (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))

#define GPIOB_BASE     0x48000400u
#define GPIOB_MODER    (*(volatile uint32_t *)(GPIOB_BASE + 0x00u))
#define GPIOB_OTYPER   (*(volatile uint32_t *)(GPIOB_BASE + 0x04u))
#define GPIOB_OSPEEDR  (*(volatile uint32_t *)(GPIOB_BASE + 0x08u))
#define GPIOB_PUPDR    (*(volatile uint32_t *)(GPIOB_BASE + 0x0Cu))
#define GPIOB_AFRL     (*(volatile uint32_t *)(GPIOB_BASE + 0x20u))

/* SPI1 (APB2) — STM32G4 enhanced SPI */
#define SPI1_BASE      0x40013000u
#define SPI1_CR1       (*(volatile uint32_t *)(SPI1_BASE + 0x00u))
#define SPI1_CR2       (*(volatile uint32_t *)(SPI1_BASE + 0x04u))
#define SPI1_SR        (*(volatile uint32_t *)(SPI1_BASE + 0x08u))
#define SPI1_DR        (*(volatile uint8_t  *)(SPI1_BASE + 0x0Cu))

/* SysTick */
#define SYST_CSR       (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR       (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR       (*(volatile uint32_t *)0xE000E018u)

static void gpioa_set_output(uint32_t pin)
{
    const uint32_t sh = pin * 2u;
    GPIOA_MODER &= ~(0x3u << sh);
    GPIOA_MODER |=  (0x1u << sh);
    GPIOA_OTYPER &= ~(1u << pin);
    GPIOA_OSPEEDR |= (0x3u << sh);
}

static void gpiob_set_af(uint32_t pin, uint32_t af)
{
    /* PB3/PB4/PB5 are in AFRL (pins 0-7) */
    const uint32_t sh    = pin * 2u;
    const uint32_t afsh  = pin * 4u;
    GPIOB_MODER &= ~(0x3u << sh);
    GPIOB_MODER |=  (0x2u << sh);
    GPIOB_OTYPER &= ~(1u << pin);
    GPIOB_OSPEEDR |= (0x3u << sh);
    GPIOB_PUPDR &= ~(0x3u << sh);
    GPIOB_AFRL &= ~(0xFu << afsh);
    GPIOB_AFRL |=  (af   << afsh);
}

static void spi1_init(void)
{
    /* PB3=SCK(AF5), PB4=MISO(AF5), PB5=MOSI(AF5) */
    gpiob_set_af(3u, 5u);
    gpiob_set_af(4u, 5u);
    gpiob_set_af(5u, 5u);

    /* Master, BR=fPCLK/256 (slow), SSM+SSI — configure before SPE */
    SPI1_CR1 = (1u << 2)  |  /* MSTR */
               (7u << 3)  |  /* BR[2:0]=111 → div256 */
               (1u << 8)  |  /* SSI */
               (1u << 9);    /* SSM */
    /* STM32G4 SPI has FIFO: FRXTH=1 sets RXNE threshold to 8-bit (not 16-bit default) */
    SPI1_CR2 = (7u << 8) | (1u << 12); /* DS=0111 (8-bit), FRXTH=1 */
    SPI1_CR1 |= (1u << 6);             /* SPE — enable after config */
}

static uint8_t spi1_transfer(uint8_t value, uint8_t *out)
{
    uint32_t timeout = 200000u;

    while ((SPI1_SR & (1u << 0)) != 0u) {  /* drain RXNE */
        (void)SPI1_DR;
    }
    while (((SPI1_SR & (1u << 1)) == 0u) && timeout-- > 0u) {}  /* TXE */
    if ((SPI1_SR & (1u << 1)) == 0u) { return 0u; }

    SPI1_DR = value;
    timeout = 200000u;
    while (((SPI1_SR & (1u << 0)) == 0u) && timeout-- > 0u) {}  /* RXNE */
    if ((SPI1_SR & (1u << 0)) == 0u) { return 0u; }

    *out = SPI1_DR;
    while ((SPI1_SR & (1u << 7)) != 0u) {}  /* BSY */
    return 1u;
}

int main(void)
{
    uint32_t phase_ms  = 0u;
    uint32_t led_ms    = 0u;
    uint8_t phase_high = 0u;
    uint8_t spi_good   = 0u;
    uint8_t tx_seed    = 0x55u;
    uint8_t mb_settled = 0u;

    RCC_AHB2ENR |= (1u << 0) | (1u << 1);  /* GPIOAEN, GPIOBEN */
    RCC_APB2ENR |= (1u << 12);              /* SPI1EN */
    (void)RCC_APB2ENR;

    gpioa_set_output(2u);
    gpioa_set_output(8u);
    spi1_init();

    GPIOA_ODR &= ~((1u << 2) | (1u << 8));

    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = (1u << 2) | (1u << 0);
    ael_mailbox_init();

    while (1) {
        if ((SYST_CSR & (1u << 16)) == 0u) { continue; }

        phase_ms += 1u;
        led_ms   += 1u;

        if (phase_ms >= 5u) {
            uint8_t rx = 0u;
            uint8_t expected;
            uint8_t ok;

            phase_ms = 0u;
            phase_high ^= 1u;
            expected = (uint8_t)(phase_high != 0u ? tx_seed : (uint8_t)~tx_seed);
            ok = spi1_transfer(expected, &rx);
            spi_good = (uint8_t)(ok != 0u && rx == expected);
            if (mb_settled == 0u) {
                if (spi_good != 0u) { ael_mailbox_pass(); }
                else { ael_mailbox_fail(0xE001u, (uint32_t)ok); }
                mb_settled = 1u;
            }

            if (spi_good != 0u && phase_high != 0u) {
                GPIOA_ODR |= (1u << 2);
            } else {
                GPIOA_ODR &= ~(1u << 2);
            }
            tx_seed = (uint8_t)(tx_seed + 0x13u);
        }

        if (led_ms >= (spi_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOA_ODR ^= (1u << 8);
        }
    }
}
