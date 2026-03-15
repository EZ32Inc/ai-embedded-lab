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

static void gpio_set_analog(GPIO_TypeDef *gpio, uint32_t pin) {
    const uint32_t shift = pin * 2u;
    gpio->MODER |= (0x3u << shift);
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

static void adc1_init(void) {
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOBEN | RCC_AHB1ENR_GPIOCEN;
    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
    (void)RCC->APB2ENR;

    gpio_set_output(GPIOA, 2u);
    gpio_set_output(GPIOB, 1u);
    gpio_set_output(GPIOC, 13u);
    gpio_set_analog(GPIOB, 0u);

    ADC->CCR = ADC_CCR_ADCPRE_0;
    ADC1->SMPR2 = ADC_SMPR2_SMP8;
    ADC1->SQR1 = 0u;
    ADC1->SQR3 = 8u;
    ADC1->CR1 = 0u;
    ADC1->CR2 = ADC_CR2_EOCS | ADC_CR2_ADON;
}

static uint8_t adc1_read(uint16_t *value_out) {
    uint32_t timeout = 200000u;

    ADC1->SR = 0u;
    ADC1->CR2 |= ADC_CR2_SWSTART;
    while (((ADC1->SR & ADC_SR_EOC) == 0u) && timeout-- > 0u) {
    }
    if ((ADC1->SR & ADC_SR_EOC) == 0u) {
        return 0u;
    }

    *value_out = (uint16_t)(ADC1->DR & 0xFFFFu);
    return 1u;
}

int main(void) {
    uint32_t phase_ms = 0u;
    uint32_t led_ms = 0u;
    uint8_t phase_high = 0u;
    uint8_t adc_good = 0u;

    adc1_init();
    GPIOA->ODR &= ~(1u << 2);
    GPIOB->ODR &= ~(1u << 1);
    GPIOC->ODR |= (1u << 13);
    systick_init_1khz();

    while (1) {
        if (systick_poll_1ms() == 0u) {
            continue;
        }

        phase_ms += 1u;
        led_ms += 1u;

        if (phase_ms >= 10u) {
            uint16_t value = 0u;
            uint8_t ok;

            phase_ms = 0u;
            phase_high ^= 1u;
            if (phase_high != 0u) {
                GPIOB->ODR |= (1u << 1);
            } else {
                GPIOB->ODR &= ~(1u << 1);
            }

            ok = adc1_read(&value);
            if (phase_high != 0u) {
                adc_good = (uint8_t)(ok != 0u && value > 2500u);
            } else {
                adc_good = (uint8_t)(ok != 0u && value < 1000u);
            }

            if (adc_good != 0u && phase_high != 0u) {
                GPIOA->ODR |= (1u << 2);
            } else {
                GPIOA->ODR &= ~(1u << 2);
            }
        }

        if (led_ms >= (adc_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOC->ODR ^= (1u << 13);
        }
    }
}
