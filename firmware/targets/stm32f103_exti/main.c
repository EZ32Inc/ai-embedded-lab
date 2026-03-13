#include <stdint.h>

#define RCC_BASE 0x40021000
#define RCC_APB2ENR (*(volatile uint32_t *)(RCC_BASE + 0x18))

#define AFIO_BASE 0x40010000
#define AFIO_EXTICR3 (*(volatile uint32_t *)(AFIO_BASE + 0x10))

#define EXTI_BASE 0x40010400
#define EXTI_IMR (*(volatile uint32_t *)(EXTI_BASE + 0x00))
#define EXTI_RTSR (*(volatile uint32_t *)(EXTI_BASE + 0x08))
#define EXTI_FTSR (*(volatile uint32_t *)(EXTI_BASE + 0x0C))
#define EXTI_PR (*(volatile uint32_t *)(EXTI_BASE + 0x14))

#define GPIOA_BASE 0x40010800
#define GPIOA_CRL (*(volatile uint32_t *)(GPIOA_BASE + 0x00))
#define GPIOA_CRH (*(volatile uint32_t *)(GPIOA_BASE + 0x04))
#define GPIOA_ODR (*(volatile uint32_t *)(GPIOA_BASE + 0x0C))

#define GPIOB_BASE 0x40010C00
#define GPIOB_CRH (*(volatile uint32_t *)(GPIOB_BASE + 0x04))
#define GPIOB_IDR (*(volatile uint32_t *)(GPIOB_BASE + 0x08))

#define GPIOC_BASE 0x40011000
#define GPIOC_CRH (*(volatile uint32_t *)(GPIOC_BASE + 0x04))
#define GPIOC_ODR (*(volatile uint32_t *)(GPIOC_BASE + 0x0C))

#define NVIC_ISER0 (*(volatile uint32_t *)0xE000E100u)

#define SYSTICK_BASE 0xE000E010u
#define SYST_CSR (*(volatile uint32_t *)(SYSTICK_BASE + 0x00u))
#define SYST_RVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x04u))
#define SYST_CVR (*(volatile uint32_t *)(SYSTICK_BASE + 0x08u))

#define RCC_AFIOEN (1u << 0)
#define RCC_IOPAEN (1u << 2)
#define RCC_IOPBEN (1u << 3)
#define RCC_IOPCEN (1u << 4)

#define SYST_CSR_ENABLE (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

static volatile uint32_t g_exti_edges = 0u;
static volatile uint8_t g_exti_saw_high = 0u;
static volatile uint8_t g_exti_saw_low = 0u;

void EXTI9_5_IRQHandler(void) {
    if ((EXTI_PR & (1u << 8)) == 0u) {
        return;
    }
    EXTI_PR = (1u << 8);
    g_exti_edges += 1u;
    if ((GPIOB_IDR & (1u << 8)) != 0u) {
        g_exti_saw_high = 1u;
    } else {
        g_exti_saw_low = 1u;
    }
}

static void exti_init(void) {
    /* PA8 = GPIO output source. */
    GPIOA_CRH &= ~(0xFu << 0);
    GPIOA_CRH |= (0x3u << 0);

    /* PB8 = input floating with EXTI on both edges. */
    GPIOB_CRH &= ~(0xFu << 0);
    GPIOB_CRH |= (0x4u << 0);

    /* Route EXTI8 to Port B. */
    AFIO_EXTICR3 &= ~0xFu;
    AFIO_EXTICR3 |= 0x1u;

    EXTI_IMR |= (1u << 8);
    EXTI_RTSR |= (1u << 8);
    EXTI_FTSR |= (1u << 8);
    EXTI_PR = (1u << 8);

    NVIC_ISER0 |= (1u << 23);
}

int main(void) {
    RCC_APB2ENR |= (RCC_AFIOEN | RCC_IOPAEN | RCC_IOPBEN | RCC_IOPCEN);

    g_exti_edges = 0u;
    g_exti_saw_high = 0u;
    g_exti_saw_low = 0u;

    /* PA4 = external machine-checkable status output. */
    GPIOA_CRL &= ~(0xFu << 16);
    GPIOA_CRL |= (0x3u << 16);

    /* PC13 = status LED. */
    GPIOC_CRH &= ~(0xFu << 20);
    GPIOC_CRH |= (0x2u << 20);
    GPIOC_ODR |= (1u << 13);

    exti_init();

    SYST_RVR = 7999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    uint32_t source_phase_ms = 0u;
    uint32_t status_phase_ms = 0u;
    uint32_t led_ms = 0u;
    uint32_t window_ms = 0u;
    uint8_t source_high = 0u;
    uint8_t status_high = 0u;
    uint8_t exti_good = 0u;

    while (1) {
        if ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {
            continue;
        }

        source_phase_ms += 1u;
        status_phase_ms += 1u;
        led_ms += 1u;
        window_ms += 1u;

        if (source_phase_ms >= 5u) {
            source_phase_ms = 0u;
            source_high ^= 1u;
            if (source_high != 0u) {
                GPIOA_ODR |= (1u << 8);
            } else {
                GPIOA_ODR &= ~(1u << 8);
            }
        }

        if (window_ms >= 100u) {
            exti_good = (uint8_t)(g_exti_edges >= 10u && g_exti_saw_high != 0u && g_exti_saw_low != 0u);
            g_exti_edges = 0u;
            g_exti_saw_high = 0u;
            g_exti_saw_low = 0u;
            window_ms = 0u;
        }

        if (status_phase_ms >= 5u) {
            status_phase_ms = 0u;
            status_high ^= 1u;
            if (exti_good != 0u && status_high != 0u) {
                GPIOA_ODR |= (1u << 4);
            } else {
                GPIOA_ODR &= ~(1u << 4);
            }
        }

        if (led_ms >= (exti_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            GPIOC_ODR ^= (1u << 13);
        }
    }
}
