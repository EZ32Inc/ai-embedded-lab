#include <stdint.h>

#define AEL_MAILBOX_ADDR 0x20004C00u
#include "../ael_mailbox.h"

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

#define RCC_AFIOEN (1u << 0)
#define RCC_IOPAEN (1u << 2)
#define RCC_IOPBEN (1u << 3)
#define RCC_IOPCEN (1u << 4)

static volatile uint32_t g_exti_edges = 0u;
static volatile uint8_t g_exti_saw_high = 0u;
static volatile uint8_t g_exti_saw_low = 0u;

static void delay_cycles(volatile uint32_t n) {
    while (n-- > 0u) {
        __asm__ volatile ("nop");
    }
}

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
    ael_mailbox_init();

    for (uint32_t i = 0; i < 16u; ++i) {
        GPIOA_ODR ^= (1u << 8);
        delay_cycles(12000u);
    }

    if (g_exti_edges < 8u || g_exti_saw_high == 0u || g_exti_saw_low == 0u) {
        ael_mailbox_fail(0xE001u, g_exti_edges);
        while (1) {
        }
    }

    ael_mailbox_pass();
    AEL_MAILBOX->detail0 = g_exti_edges;
    GPIOA_ODR |= (1u << 4);

    while (1) {
        delay_cycles(200000u);
        GPIOA_ODR ^= (1u << 8);
        GPIOC_ODR ^= (1u << 13);
        AEL_MAILBOX->detail0 += 1u;
    }
}
