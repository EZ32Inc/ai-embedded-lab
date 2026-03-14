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

static void gpio_set_input(GPIO_TypeDef *gpio, uint32_t pin) {
    const uint32_t shift = pin * 2u;
    gpio->MODER &= ~(0x3u << shift);
    gpio->PUPDR &= ~(0x3u << shift);
}

static void systick_init_1khz(void) {
    SysTick->LOAD = 16000u - 1u;
    SysTick->VAL = 0u;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk;
}

static uint8_t systick_poll_1ms(void) {
    return (uint8_t)((SysTick->CTRL & SysTick_CTRL_COUNTFLAG_Msk) != 0u);
}

int main(void) {
    uint32_t drive_ms = 0u;
    uint32_t sense_ms = 0u;
    uint32_t status_ms = 0u;
    uint32_t led_ms = 0u;
    uint8_t drive_high = 0u;
    uint8_t status_high = 0u;
    uint8_t saw_high = 0u;
    uint8_t saw_low = 0u;
    uint8_t loopback_good = 0u;

    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOCEN;
    (void)RCC->AHB1ENR;

    gpio_set_output(GPIOA, 2u);
    gpio_set_output(GPIOA, 8u);
    gpio_set_input(GPIOA, 6u);
    gpio_set_output(GPIOC, 13u);

    GPIOA->ODR &= ~((1u << 2) | (1u << 8));
    GPIOC->ODR |= (1u << 13);
    systick_init_1khz();

    while (1) {
        if (systick_poll_1ms() == 0u) {
            continue;
        }

        drive_ms += 1u;
        sense_ms += 1u;
        status_ms += 1u;
        led_ms += 1u;

        if (drive_ms >= 5u) {
            drive_ms = 0u;
            drive_high ^= 1u;
            if (drive_high != 0u) {
                GPIOA->ODR |= (1u << 8);
            } else {
                GPIOA->ODR &= ~(1u << 8);
            }
        }

        if ((GPIOA->IDR & GPIO_IDR_ID6) != 0u) {
            saw_high = 1u;
        } else {
            saw_low = 1u;
        }

        if (sense_ms >= 100u) {
            loopback_good = (uint8_t)(saw_high != 0u && saw_low != 0u);
            saw_high = 0u;
            saw_low = 0u;
            sense_ms = 0u;
        }

        if (status_ms >= 10u) {
            status_ms = 0u;
            status_high ^= 1u;
            if (loopback_good != 0u && status_high != 0u) {
                GPIOA->ODR |= (1u << 2);
            } else {
                GPIOA->ODR &= ~(1u << 2);
            }
        }

        if (led_ms >= (loopback_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOC->ODR ^= (1u << 13);
        }
    }
}
