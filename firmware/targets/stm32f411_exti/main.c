#include "stm32f411xe.h"

void __libc_init_array(void) {
}

static volatile uint32_t g_exti_edges = 0u;
static volatile uint8_t g_exti_saw_high = 0u;
static volatile uint8_t g_exti_saw_low = 0u;

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

void EXTI9_5_IRQHandler(void) {
    if ((EXTI->PR & EXTI_PR_PR6) == 0u) {
        return;
    }

    EXTI->PR = EXTI_PR_PR6;
    g_exti_edges += 1u;
    if ((GPIOA->IDR & GPIO_IDR_ID6) != 0u) {
        g_exti_saw_high = 1u;
    } else {
        g_exti_saw_low = 1u;
    }
}

static void exti6_init(void) {
    gpio_set_output(GPIOA, 8u);
    gpio_set_input(GPIOA, 6u);

    SYSCFG->EXTICR[1] &= ~(0xFu << 8);
    EXTI->IMR |= EXTI_IMR_MR6;
    EXTI->RTSR |= EXTI_RTSR_TR6;
    EXTI->FTSR |= EXTI_FTSR_TR6;
    EXTI->PR = EXTI_PR_PR6;
    NVIC_EnableIRQ(EXTI9_5_IRQn);
}

int main(void) {
    uint32_t drive_ms = 0u;
    uint32_t status_ms = 0u;
    uint32_t window_ms = 0u;
    uint32_t led_ms = 0u;
    uint8_t drive_high = 0u;
    uint8_t status_high = 0u;
    uint8_t exti_good = 0u;

    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOCEN;
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    (void)RCC->APB2ENR;

    gpio_set_output(GPIOA, 2u);
    gpio_set_output(GPIOC, 13u);
    exti6_init();

    GPIOA->ODR &= ~((1u << 2) | (1u << 8));
    GPIOC->ODR |= (1u << 13);
    systick_init_1khz();

    while (1) {
        if (systick_poll_1ms() == 0u) {
            continue;
        }

        drive_ms += 1u;
        status_ms += 1u;
        window_ms += 1u;
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

        if (window_ms >= 100u) {
            exti_good = (uint8_t)(g_exti_edges >= 10u && g_exti_saw_high != 0u && g_exti_saw_low != 0u);
            g_exti_edges = 0u;
            g_exti_saw_high = 0u;
            g_exti_saw_low = 0u;
            window_ms = 0u;
        }

        if (status_ms >= 10u) {
            status_ms = 0u;
            status_high ^= 1u;
            if (exti_good != 0u && status_high != 0u) {
                GPIOA->ODR |= (1u << 2);
            } else {
                GPIOA->ODR &= ~(1u << 2);
            }
        }

        if (led_ms >= (exti_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOC->ODR ^= (1u << 13);
        }
    }
}
