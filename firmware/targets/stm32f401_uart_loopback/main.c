#include "stm32f401xc.h"

void __libc_init_array(void) {
}

static void gpio_set_output(GPIO_TypeDef *gpio, uint32_t pin) {
    const uint32_t shift = pin * 2u;
    gpio->MODER &= ~(0x3u << shift);
    gpio->MODER |= (0x1u << shift);
    gpio->OTYPER &= ~(1u << pin);
    gpio->OSPEEDR |= (0x3u << shift);
    gpio->PUPDR &= ~(0x3u << shift);
}

static void gpio_set_af(GPIO_TypeDef *gpio, uint32_t pin, uint32_t af) {
    const uint32_t shift = pin * 2u;
    const uint32_t index = pin >> 3;
    const uint32_t afr_shift = (pin & 0x7u) * 4u;
    gpio->MODER &= ~(0x3u << shift);
    gpio->MODER |= (0x2u << shift);
    gpio->OTYPER &= ~(1u << pin);
    gpio->OSPEEDR |= (0x3u << shift);
    gpio->PUPDR &= ~(0x3u << shift);
    gpio->AFR[index] &= ~(0xFu << afr_shift);
    gpio->AFR[index] |= (af << afr_shift);
}

static void systick_init_1khz(void) {
    SysTick->LOAD = 16000u - 1u;
    SysTick->VAL = 0u;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk;
}

static uint8_t systick_poll_1ms(void) {
    return (uint8_t)((SysTick->CTRL & SysTick_CTRL_COUNTFLAG_Msk) != 0u);
}

static void usart1_init(void) {
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOCEN;
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;
    (void)RCC->APB2ENR;

    gpio_set_output(GPIOA, 2u);
    gpio_set_output(GPIOC, 13u);
    gpio_set_af(GPIOA, 9u, 7u);
    gpio_set_af(GPIOA, 10u, 7u);

    USART1->BRR = 139u;
    USART1->CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
}

static uint8_t usart1_transfer(uint8_t value, uint8_t *out) {
    uint32_t timeout = 200000u;

    while ((USART1->SR & USART_SR_RXNE) != 0u) {
        (void)USART1->DR;
    }

    while (((USART1->SR & USART_SR_TXE) == 0u) && timeout-- > 0u) {
    }
    if ((USART1->SR & USART_SR_TXE) == 0u) {
        return 0u;
    }

    USART1->DR = value;
    timeout = 200000u;
    while (((USART1->SR & USART_SR_RXNE) == 0u) && timeout-- > 0u) {
    }
    if ((USART1->SR & USART_SR_RXNE) == 0u) {
        return 0u;
    }

    *out = (uint8_t)USART1->DR;
    return 1u;
}

int main(void) {
    uint32_t phase_ms = 0u;
    uint32_t led_ms = 0u;
    uint8_t phase_high = 0u;
    uint8_t uart_good = 0u;
    uint8_t tx_seed = 0x55u;

    usart1_init();
    GPIOA->ODR &= ~(1u << 2);
    GPIOC->ODR |= (1u << 13);
    systick_init_1khz();

    while (1) {
        if (systick_poll_1ms() == 0u) {
            continue;
        }

        phase_ms += 1u;
        led_ms += 1u;

        if (phase_ms >= 10u) {
            uint8_t rx = 0u;
            uint8_t expected;
            uint8_t ok;

            phase_ms = 0u;
            phase_high ^= 1u;
            expected = (uint8_t)(phase_high != 0u ? tx_seed : (uint8_t)~tx_seed);
            ok = usart1_transfer(expected, &rx);
            uart_good = (uint8_t)(ok != 0u && rx == expected);

            if (uart_good != 0u && phase_high != 0u) {
                GPIOA->ODR |= (1u << 2);
            } else {
                GPIOA->ODR &= ~(1u << 2);
            }

            tx_seed = (uint8_t)(tx_seed + 0x11u);
        }

        if (led_ms >= (uart_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOC->ODR ^= (1u << 13);
        }
    }
}
