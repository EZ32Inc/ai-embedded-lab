#include "stm32f411xe.h"

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

static void spi2_init(void) {
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOBEN | RCC_AHB1ENR_GPIOCEN;
    RCC->APB1ENR |= RCC_APB1ENR_SPI2EN;
    (void)RCC->APB1ENR;

    gpio_set_output(GPIOA, 2u);
    gpio_set_output(GPIOA, 3u);
    gpio_set_output(GPIOC, 13u);
    gpio_set_af(GPIOB, 13u, 5u);
    gpio_set_af(GPIOB, 14u, 5u);
    gpio_set_af(GPIOB, 15u, 5u);

    /* APB1 @ 16 MHz, BR=/256 -> SCK about 62.5 kHz for manual/LA capture. */
    SPI2->CR1 = SPI_CR1_MSTR
        | SPI_CR1_BR_0 | SPI_CR1_BR_1 | SPI_CR1_BR_2
        | SPI_CR1_SSI | SPI_CR1_SSM | SPI_CR1_SPE;
}

static uint8_t spi2_transfer(uint8_t value, uint8_t *out) {
    uint32_t timeout = 200000u;

    while ((SPI2->SR & SPI_SR_RXNE) != 0u) {
        (void)SPI2->DR;
    }
    while (((SPI2->SR & SPI_SR_TXE) == 0u) && timeout-- > 0u) {
    }
    if ((SPI2->SR & SPI_SR_TXE) == 0u) {
        return 0u;
    }

    *(__IO uint8_t *)&SPI2->DR = value;
    timeout = 200000u;
    while (((SPI2->SR & SPI_SR_RXNE) == 0u) && timeout-- > 0u) {
    }
    if ((SPI2->SR & SPI_SR_RXNE) == 0u) {
        return 0u;
    }

    *out = *(__IO uint8_t *)&SPI2->DR;
    while ((SPI2->SR & SPI_SR_BSY) != 0u) {
    }
    return 1u;
}

int main(void) {
    uint32_t led_ms = 0u;
    uint8_t tx = 0x55u;

    spi2_init();
    GPIOA->ODR &= ~((1u << 2) | (1u << 3));
    GPIOC->ODR |= (1u << 13);
    systick_init_1khz();

    while (1) {
        uint8_t rx = 0u;
        uint8_t ok = spi2_transfer(tx, &rx);

        if (ok != 0u) {
            GPIOA->ODR ^= (1u << 3);
            if (rx == tx) {
                GPIOA->ODR ^= (1u << 2);
            } else {
                GPIOA->ODR &= ~(1u << 2);
            }
        } else {
            GPIOA->ODR &= ~((1u << 2) | (1u << 3));
        }

        tx = (uint8_t)(tx + 0x3Du);

        if (systick_poll_1ms() != 0u) {
            led_ms += 1u;
            if (led_ms >= 250u) {
                led_ms = 0u;
                GPIOC->ODR ^= (1u << 13);
            }
        }
    }
}
