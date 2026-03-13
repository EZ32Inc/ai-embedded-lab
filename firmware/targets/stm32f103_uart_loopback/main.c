#include <stdint.h>

#define PERIPH_BASE        0x40000000u
#define APB2PERIPH_BASE    (PERIPH_BASE + 0x10000u)
#define AHBPERIPH_BASE     (PERIPH_BASE + 0x20000u)

#define RCC_BASE           (AHBPERIPH_BASE + 0x1000u)
#define GPIOA_BASE         (APB2PERIPH_BASE + 0x0800u)
#define GPIOC_BASE         (APB2PERIPH_BASE + 0x1000u)
#define USART1_BASE        (APB2PERIPH_BASE + 0x3800u)

#define RCC_APB2ENR        (*(volatile uint32_t *)(RCC_BASE + 0x18u))
#define GPIOA_CRL          (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_CRH          (*(volatile uint32_t *)(GPIOA_BASE + 0x04u))
#define GPIOA_ODR          (*(volatile uint32_t *)(GPIOA_BASE + 0x0Cu))
#define GPIOC_CRH          (*(volatile uint32_t *)(GPIOC_BASE + 0x04u))
#define GPIOC_ODR          (*(volatile uint32_t *)(GPIOC_BASE + 0x0Cu))

#define USART1_SR          (*(volatile uint32_t *)(USART1_BASE + 0x00u))
#define USART1_DR          (*(volatile uint32_t *)(USART1_BASE + 0x04u))
#define USART1_BRR         (*(volatile uint32_t *)(USART1_BASE + 0x08u))
#define USART1_CR1         (*(volatile uint32_t *)(USART1_BASE + 0x0Cu))

#define RCC_APB2ENR_IOPAEN (1u << 2)
#define RCC_APB2ENR_IOPCEN (1u << 4)
#define RCC_APB2ENR_USART1EN (1u << 14)

#define USART_SR_RXNE      (1u << 5)
#define USART_SR_TXE       (1u << 7)
#define USART_CR1_UE       (1u << 13)
#define USART_CR1_TE       (1u << 3)
#define USART_CR1_RE       (1u << 2)

static void delay_cycles(volatile uint32_t n) {
    while (n-- > 0u) {
        __asm__ volatile ("nop");
    }
}

static void delay_ms(uint32_t ms) {
    while (ms-- > 0u) {
        delay_cycles(8000u);
    }
}

static void usart1_init(void) {
    RCC_APB2ENR |= RCC_APB2ENR_IOPAEN | RCC_APB2ENR_IOPCEN | RCC_APB2ENR_USART1EN;

    /* PA4 output push-pull, 2MHz. */
    GPIOA_CRL &= ~(0xFu << 16);
    GPIOA_CRL |= (0x2u << 16);

    /* PA9 = USART1_TX AF push-pull 2MHz, PA10 = USART1_RX input floating. */
    GPIOA_CRH &= ~(0xFFu << 4);
    GPIOA_CRH |= (0x0Bu << 4) | (0x04u << 8);

    /* PC13 output push-pull, 2MHz. */
    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x2u << 20);

    USART1_BRR = 0x1D4Cu; /* 72 MHz / 115200 */
    USART1_CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
}

static uint8_t usart1_transfer(uint8_t value, uint8_t *out) {
    uint32_t timeout = 200000u;

    /* Drain stale receive data. */
    while ((USART1_SR & USART_SR_RXNE) != 0u) {
        (void)USART1_DR;
    }

    while (((USART1_SR & USART_SR_TXE) == 0u) && timeout-- > 0u) {
    }
    if ((USART1_SR & USART_SR_TXE) == 0u) {
        return 0u;
    }

    USART1_DR = value;

    timeout = 200000u;
    while (((USART1_SR & USART_SR_RXNE) == 0u) && timeout-- > 0u) {
    }
    if ((USART1_SR & USART_SR_RXNE) == 0u) {
        return 0u;
    }

    *out = (uint8_t)USART1_DR;
    return 1u;
}

int main(void) {
    uint32_t led_ticks = 0u;
    uint8_t phase_high = 0u;
    uint8_t uart_good = 0u;
    const uint8_t tx_low = 0x55u;
    const uint8_t tx_high = 0xA5u;

    usart1_init();
    GPIOA_ODR &= ~(1u << 4);
    GPIOC_ODR |= (1u << 13);

    while (1) {
        uint8_t expected;
        uint8_t rx = 0u;
        uint8_t ok;
        uint32_t led_period_ms;

        phase_high ^= 1u;
        expected = (phase_high != 0u) ? tx_high : tx_low;
        ok = usart1_transfer(expected, &rx);
        uart_good = (uint8_t)(ok != 0u && rx == expected);

        if (phase_high == 0u) {
            GPIOA_ODR &= ~(1u << 4);
        } else if (uart_good != 0u) {
            GPIOA_ODR |= (1u << 4);
        } else {
            GPIOA_ODR &= ~(1u << 4);
        }

        led_period_ms = (uart_good != 0u) ? 500u : 250u;
        led_ticks += 5u;
        if (led_ticks >= led_period_ms) {
            GPIOC_ODR ^= (1u << 13);
            led_ticks = 0u;
        }

        delay_ms(5u);
    }
}
