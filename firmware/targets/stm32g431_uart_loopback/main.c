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
#define GPIOA_PUPDR    (*(volatile uint32_t *)(GPIOA_BASE + 0x0Cu))
#define GPIOA_ODR      (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))
#define GPIOA_AFRH     (*(volatile uint32_t *)(GPIOA_BASE + 0x24u))

/* USART1 (APB2) — G431 new-style register map */
#define USART1_BASE    0x40013800u
#define USART1_CR1     (*(volatile uint32_t *)(USART1_BASE + 0x00u))
#define USART1_BRR     (*(volatile uint32_t *)(USART1_BASE + 0x0Cu))
#define USART1_ISR     (*(volatile uint32_t *)(USART1_BASE + 0x1Cu))
#define USART1_ICR     (*(volatile uint32_t *)(USART1_BASE + 0x20u))
#define USART1_RDR     (*(volatile uint32_t *)(USART1_BASE + 0x24u))
#define USART1_TDR     (*(volatile uint32_t *)(USART1_BASE + 0x28u))

/* SysTick */
#define SYST_CSR       (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR       (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR       (*(volatile uint32_t *)0xE000E018u)

static void gpio_set_output(volatile uint32_t *moder, volatile uint32_t *otyper,
                             volatile uint32_t *ospeedr, uint32_t pin)
{
    const uint32_t sh = pin * 2u;
    *moder &= ~(0x3u << sh);
    *moder |=  (0x1u << sh);
    *otyper &= ~(1u << pin);
    *ospeedr |= (0x3u << sh);
}

static void gpio_set_af(volatile uint32_t *moder, volatile uint32_t *otyper,
                        volatile uint32_t *ospeedr, volatile uint32_t *afrh,
                        uint32_t pin, uint32_t af)
{
    /* pin must be >= 8 (AFRH covers pins 8-15) */
    const uint32_t sh = pin * 2u;
    const uint32_t afsh = (pin - 8u) * 4u;
    *moder &= ~(0x3u << sh);
    *moder |=  (0x2u << sh);
    *otyper &= ~(1u << pin);
    *ospeedr |= (0x3u << sh);
    *afrh &= ~(0xFu << afsh);
    *afrh |=  (af   << afsh);
}

static void usart1_init(void)
{
    /* PA9=TX(AF7), PA10=RX(AF7) — pins 9 and 10 are in AFRH */
    gpio_set_af(&GPIOA_MODER, &GPIOA_OTYPER, &GPIOA_OSPEEDR, &GPIOA_AFRH, 9u, 7u);
    gpio_set_af(&GPIOA_MODER, &GPIOA_OTYPER, &GPIOA_OSPEEDR, &GPIOA_AFRH, 10u, 7u);

    /* BRR = 16MHz / 115200 = 139 */
    USART1_BRR = 139u;
    /* UE=bit0, TE=bit3, RE=bit2 */
    USART1_CR1 = (1u << 0) | (1u << 3) | (1u << 2);
}

static uint8_t usart1_transfer(uint8_t value, uint8_t *out)
{
    uint32_t timeout = 200000u;

    /* Flush RX */
    while ((USART1_ISR & (1u << 5)) != 0u) {
        (void)USART1_RDR;
    }
    /* Wait TXE (bit7) */
    while (((USART1_ISR & (1u << 7)) == 0u) && timeout-- > 0u) {}
    if ((USART1_ISR & (1u << 7)) == 0u) { return 0u; }

    USART1_TDR = value;
    timeout = 200000u;
    /* Wait RXNE (bit5) */
    while (((USART1_ISR & (1u << 5)) == 0u) && timeout-- > 0u) {}
    if ((USART1_ISR & (1u << 5)) == 0u) { return 0u; }

    *out = (uint8_t)(USART1_RDR & 0xFFu);
    return 1u;
}

int main(void)
{
    uint32_t phase_ms = 0u;
    uint32_t led_ms   = 0u;
    uint8_t phase_high = 0u;
    uint8_t uart_good  = 0u;
    uint8_t tx_seed    = 0x55u;
    uint8_t mb_settled = 0u;

    /* Clocks: GPIOA on AHB2, USART1 on APB2 */
    RCC_AHB2ENR |= (1u << 0);   /* GPIOAEN */
    RCC_APB2ENR |= (1u << 14);  /* USART1EN */
    (void)RCC_APB2ENR;          /* pipeline flush */

    gpio_set_output(&GPIOA_MODER, &GPIOA_OTYPER, &GPIOA_OSPEEDR, 2u);
    gpio_set_output(&GPIOA_MODER, &GPIOA_OTYPER, &GPIOA_OSPEEDR, 8u);

    usart1_init();

    GPIOA_ODR &= ~(1u << 2);
    GPIOA_ODR &= ~(1u << 8);

    /* SysTick 1kHz from 16MHz HSI */
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
            ok = usart1_transfer(expected, &rx);
            uart_good = (uint8_t)(ok != 0u && rx == expected);
            if (mb_settled == 0u) {
                if (uart_good != 0u) { ael_mailbox_pass(); }
                else { ael_mailbox_fail(0xE001u, (uint32_t)ok); }
                mb_settled = 1u;
            }

            if (uart_good != 0u && phase_high != 0u) {
                GPIOA_ODR |= (1u << 2);
            } else {
                GPIOA_ODR &= ~(1u << 2);
            }
            tx_seed = (uint8_t)(tx_seed + 0x11u);
        }

        if (led_ms >= (uart_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOA_ODR ^= (1u << 8);
        }
    }
}
