#include <stdint.h>

#define RCC_BASE 0x40021000
#define RCC_APB2ENR (*(volatile uint32_t *)(RCC_BASE + 0x18))

#define GPIOA_BASE 0x40010800
#define GPIOA_CRL (*(volatile uint32_t *)(GPIOA_BASE + 0x00))
#define GPIOA_CRH (*(volatile uint32_t *)(GPIOA_BASE + 0x04))
#define GPIOA_ODR (*(volatile uint32_t *)(GPIOA_BASE + 0x0C))

#define GPIOC_BASE 0x40011000
#define GPIOC_CRH (*(volatile uint32_t *)(GPIOC_BASE + 0x04))
#define GPIOC_ODR (*(volatile uint32_t *)(GPIOC_BASE + 0x0C))

#define USART1_BASE 0x40013800
#define USART1_SR (*(volatile uint32_t *)(USART1_BASE + 0x00))
#define USART1_DR (*(volatile uint32_t *)(USART1_BASE + 0x04))
#define USART1_BRR (*(volatile uint32_t *)(USART1_BASE + 0x08))
#define USART1_CR1 (*(volatile uint32_t *)(USART1_BASE + 0x0C))

#define ADC1_BASE 0x40012400
#define ADC1_SR (*(volatile uint32_t *)(ADC1_BASE + 0x00))
#define ADC1_CR2 (*(volatile uint32_t *)(ADC1_BASE + 0x08))
#define ADC1_SMPR2 (*(volatile uint32_t *)(ADC1_BASE + 0x10))
#define ADC1_SQR3 (*(volatile uint32_t *)(ADC1_BASE + 0x34))
#define ADC1_DR (*(volatile uint32_t *)(ADC1_BASE + 0x4C))

#define SYSTICK_BASE 0xE000E010u
#define SYST_CSR (*(volatile uint32_t *)(SYSTICK_BASE + 0x00u))
#define SYST_RVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x04u))
#define SYST_CVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x08u))

#define RCC_IOPAEN (1u << 2)
#define RCC_IOPCEN (1u << 4)
#define RCC_ADC1EN (1u << 9)
#define RCC_USART1EN (1u << 14)
#define USART_SR_TXE (1u << 7)
#define USART_CR1_UE (1u << 13)
#define USART_CR1_TE (1u << 3)
#define ADC_CR2_ADON (1u << 0)
#define ADC_CR2_SWSTART (1u << 22)
#define ADC_CR2_EXTTRIG (1u << 20)
#define ADC_SR_EOC (1u << 1)
#define SYST_CSR_ENABLE (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

static void uart1_init(void) {
    GPIOA_CRH &= ~(0xFu << 4);
    GPIOA_CRH |= (0xBu << 4);
    USART1_BRR = 0x45u;
    USART1_CR1 = USART_CR1_UE | USART_CR1_TE;
}

static void uart1_write_str(const char *s) {
    while (*s != '\0') {
        while ((USART1_SR & USART_SR_TXE) == 0u) {
        }
        USART1_DR = (uint32_t)(uint8_t)(*s++);
    }
}

static void uart1_write_u32(uint32_t value) {
    char buf[11];
    int i = 10;
    buf[i--] = '\0';
    if (value == 0u) {
        buf[i] = '0';
        uart1_write_str(&buf[i]);
        return;
    }
    while (value > 0u && i >= 0) {
        buf[i--] = (char)('0' + (value % 10u));
        value /= 10u;
    }
    uart1_write_str(&buf[i + 1]);
}

static void adc1_init(void) {
    GPIOA_CRL &= ~(0xFu << 0);
    ADC1_SMPR2 |= (0x7u << 0);
    ADC1_SQR3 = 0u;
    ADC1_CR2 = ADC_CR2_ADON;
}

static uint16_t adc1_read(void) {
    ADC1_CR2 |= ADC_CR2_EXTTRIG | ADC_CR2_SWSTART | ADC_CR2_ADON;
    while ((ADC1_SR & ADC_SR_EOC) == 0u) {
    }
    return (uint16_t)(ADC1_DR & 0xFFFFu);
}

int main(void) {
    RCC_APB2ENR |= (RCC_IOPAEN | RCC_IOPCEN | RCC_ADC1EN | RCC_USART1EN);

    GPIOA_CRL &= ~(0xFFFFu << 16);
    GPIOA_CRL |= (0x3333u << 16);
    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x2u << 20);
    GPIOC_ODR |= (1u << 13);

    uart1_init();
    adc1_init();
    uart1_write_str("AEL_READY STM32F103 ADC\r\n");

    SYST_RVR = 7999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    uint32_t div0 = 0;
    uint32_t div1 = 0;
    uint32_t div2 = 0;
    uint32_t div3 = 0;
    uint32_t led_ms = 0;
    uint32_t banner_ms = 0;
    while (1) {
        if (++div0 >= 200) {
            div0 = 0;
            GPIOA_ODR ^= (1u << 4);
        }
        if (++div1 >= 400) {
            div1 = 0;
            GPIOA_ODR ^= (1u << 5);
        }
        if (++div2 >= 600) {
            div2 = 0;
            GPIOA_ODR ^= (1u << 6);
        }
        if (++div3 >= 800) {
            div3 = 0;
            GPIOA_ODR ^= (1u << 7);
        }

        if ((SYST_CSR & SYST_CSR_COUNTFLAG) != 0u) {
            led_ms += 1u;
            banner_ms += 1u;
        }
        if (led_ms >= 500u) {
            led_ms = 0u;
            GPIOC_ODR ^= (1u << 13);
        }
        if (banner_ms >= 1000u) {
            uint16_t sample = adc1_read();
            banner_ms = 0u;
            uart1_write_str("AEL_READY STM32F103 ADC sample=");
            uart1_write_u32(sample);
            uart1_write_str("\r\n");
        }
    }
}
