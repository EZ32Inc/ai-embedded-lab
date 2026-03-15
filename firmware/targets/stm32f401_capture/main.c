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

static void tim1_source_init(void) {
    gpio_set_af(GPIOA, 8u, 1u);
    TIM1->PSC = 16000u - 1u;
    TIM1->ARR = 20u - 1u;
    TIM1->CCR1 = 10u;
    TIM1->CCMR1 = TIM_CCMR1_OC1PE | TIM_CCMR1_OC1M_1 | TIM_CCMR1_OC1M_2;
    TIM1->CCER = TIM_CCER_CC1E;
    TIM1->BDTR = TIM_BDTR_MOE;
    TIM1->EGR = TIM_EGR_UG;
    TIM1->CR1 = TIM_CR1_ARPE | TIM_CR1_CEN;
}

static void tim3_capture_init(void) {
    gpio_set_af(GPIOA, 6u, 2u);
    TIM3->PSC = 1600u - 1u;
    TIM3->ARR = 0xFFFFu;
    TIM3->CNT = 0u;
    TIM3->CCMR1 = TIM_CCMR1_CC1S_0;
    TIM3->CCER = TIM_CCER_CC1E;
    TIM3->EGR = TIM_EGR_UG;
    TIM3->SR = 0u;
    TIM3->CR1 = TIM_CR1_CEN;
}

int main(void) {
    uint32_t status_ms = 0u;
    uint32_t window_ms = 0u;
    uint32_t led_ms = 0u;
    uint8_t status_high = 0u;
    uint8_t capture_good = 0u;
    uint8_t have_last = 0u;
    uint16_t last_capture = 0u;
    uint32_t capture_count = 0u;
    uint32_t good_periods = 0u;

    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOCEN;
    RCC->APB2ENR |= RCC_APB2ENR_TIM1EN;
    RCC->APB1ENR |= RCC_APB1ENR_TIM3EN;
    (void)RCC->APB1ENR;

    gpio_set_output(GPIOA, 2u);
    gpio_set_output(GPIOC, 13u);
    tim1_source_init();
    tim3_capture_init();

    GPIOA->ODR &= ~(1u << 2);
    GPIOC->ODR |= (1u << 13);
    systick_init_1khz();

    while (1) {
        if ((TIM3->SR & TIM_SR_CC1IF) != 0u) {
            const uint16_t current = (uint16_t)TIM3->CCR1;
            TIM3->SR &= ~TIM_SR_CC1IF;
            if (have_last != 0u) {
                const uint16_t delta = (uint16_t)(current - last_capture);
                if (delta >= 150u && delta <= 250u) {
                    good_periods += 1u;
                }
            } else {
                have_last = 1u;
            }
            last_capture = current;
            capture_count += 1u;
        }

        if (systick_poll_1ms() == 0u) {
            continue;
        }

        status_ms += 1u;
        window_ms += 1u;
        led_ms += 1u;

        if (window_ms >= 100u) {
            capture_good = (uint8_t)(capture_count >= 3u && good_periods >= 2u);
            capture_count = 0u;
            good_periods = 0u;
            window_ms = 0u;
        }

        if (status_ms >= 10u) {
            status_ms = 0u;
            status_high ^= 1u;
            if (capture_good != 0u && status_high != 0u) {
                GPIOA->ODR |= (1u << 2);
            } else {
                GPIOA->ODR &= ~(1u << 2);
            }
        }

        if (led_ms >= (capture_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOC->ODR ^= (1u << 13);
        }
    }
}
