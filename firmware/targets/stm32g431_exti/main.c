#include <stdint.h>
#include "../ael_mailbox.h"

/* STM32G431 — GPIO on AHB2 */
#define RCC_BASE       0x40021000u
#define RCC_AHB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x4Cu))
#define RCC_APB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x60u))

#define GPIOA_BASE     0x48000000u
#define GPIOA_MODER    (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_OTYPER   (*(volatile uint32_t *)(GPIOA_BASE + 0x04u))
#define GPIOA_OSPEEDR  (*(volatile uint32_t *)(GPIOA_BASE + 0x08u))
#define GPIOA_PUPDR    (*(volatile uint32_t *)(GPIOA_BASE + 0x0Cu))
#define GPIOA_IDR      (*(volatile uint32_t *)(GPIOA_BASE + 0x10u))
#define GPIOA_ODR      (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))

/* SYSCFG (APB2) — for EXTI source selection */
#define SYSCFG_BASE    0x40010000u
#define SYSCFG_EXTICR2 (*(volatile uint32_t *)(SYSCFG_BASE + 0x0Cu))

/* EXTI (G431 base 0x40010400) */
#define EXTI_BASE      0x40010400u
#define EXTI_IMR1      (*(volatile uint32_t *)(EXTI_BASE + 0x00u))
#define EXTI_RTSR1     (*(volatile uint32_t *)(EXTI_BASE + 0x08u))
#define EXTI_FTSR1     (*(volatile uint32_t *)(EXTI_BASE + 0x0Cu))
#define EXTI_PR1       (*(volatile uint32_t *)(EXTI_BASE + 0x14u))

/* SysTick */
#define SYST_CSR       (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR       (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR       (*(volatile uint32_t *)0xE000E018u)

static void gpioa_set_output(uint32_t pin)
{
    const uint32_t sh = pin * 2u;
    GPIOA_MODER &= ~(0x3u << sh);
    GPIOA_MODER |=  (0x1u << sh);
    GPIOA_OTYPER &= ~(1u << pin);
    GPIOA_OSPEEDR |= (0x3u << sh);
}

static void gpioa_set_input(uint32_t pin)
{
    const uint32_t sh = pin * 2u;
    GPIOA_MODER &= ~(0x3u << sh);
    GPIOA_PUPDR &= ~(0x3u << sh);
}

static void exti6_init(void)
{
    /* PA6 = EXTI line 6; SYSCFG_EXTICR2 bits [7:4] = 0000 (port A) */
    SYSCFG_EXTICR2 &= ~(0xFu << 4);

    /* Unmask line 6, enable rising+falling triggers */
    EXTI_IMR1  |= (1u << 6);
    EXTI_RTSR1 |= (1u << 6);
    EXTI_FTSR1 |= (1u << 6);
    EXTI_PR1    = (1u << 6);   /* clear any pending */
}

int main(void)
{
    uint32_t drive_ms  = 0u;
    uint32_t status_ms = 0u;
    uint32_t window_ms = 0u;
    uint32_t led_ms    = 0u;
    uint8_t drive_high  = 0u;
    uint8_t status_high = 0u;
    uint8_t exti_good   = 0u;
    uint8_t mb_settled  = 0u;
    uint32_t exti_edges = 0u;
    uint8_t saw_high    = 0u;
    uint8_t saw_low     = 0u;

    RCC_AHB2ENR |= (1u << 0);   /* GPIOAEN */
    RCC_APB2ENR |= (1u << 0);   /* SYSCFGEN */
    (void)RCC_APB2ENR;

    gpioa_set_output(2u);   /* PA2: signal */
    gpioa_set_output(8u);   /* PA8: output → drives PA6 via loopback */
    gpioa_set_input(6u);    /* PA6: EXTI input */

    exti6_init();

    GPIOA_ODR &= ~((1u << 2) | (1u << 8));

    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = (1u << 2) | (1u << 0);
    ael_mailbox_init();

    while (1) {
        /* Poll EXTI pending (no interrupt — startup has no device vectors) */
        if ((EXTI_PR1 & (1u << 6)) != 0u) {
            EXTI_PR1 = (1u << 6);   /* clear by writing 1 */
            exti_edges += 1u;
            if ((GPIOA_IDR & (1u << 6)) != 0u) {
                saw_high = 1u;
            } else {
                saw_low = 1u;
            }
        }

        if ((SYST_CSR & (1u << 16)) == 0u) { continue; }

        drive_ms  += 1u;
        status_ms += 1u;
        window_ms += 1u;
        led_ms    += 1u;

        /* Toggle PA8 every 5ms → 100Hz square wave into PA6 EXTI */
        if (drive_ms >= 5u) {
            drive_ms = 0u;
            drive_high ^= 1u;
            if (drive_high != 0u) {
                GPIOA_ODR |= (1u << 8);
            } else {
                GPIOA_ODR &= ~(1u << 8);
            }
        }

        /* Evaluate window every 100ms: expect >=10 edges and saw both levels */
        if (window_ms >= 100u) {
            exti_good  = (uint8_t)(exti_edges >= 10u && saw_high != 0u && saw_low != 0u);
            exti_edges = 0u;
            saw_high   = 0u;
            saw_low    = 0u;
            window_ms  = 0u;
            if (mb_settled == 0u) {
                if (exti_good != 0u) { ael_mailbox_pass(); }
                else { ael_mailbox_fail(0xE001u, 0u); }
                mb_settled = 1u;
            }
        }

        if (status_ms >= 5u) {
            status_ms = 0u;
            status_high ^= 1u;
            if (exti_good != 0u && status_high != 0u) {
                GPIOA_ODR |= (1u << 2);
            } else {
                GPIOA_ODR &= ~(1u << 2);
            }
        }

        if (led_ms >= (exti_good != 0u ? 500u : 250u)) {
            led_ms = 0u;
            /* PA8 is driven by the test — LED blinks at drive rate, skip separate toggle */
        }
    }
}
