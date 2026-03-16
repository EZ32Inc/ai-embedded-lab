#include <stdint.h>
#include "../ael_mailbox.h"

/* STM32G431 — GPIO on AHB2 */
#define RCC_BASE       0x40021000u
#define RCC_AHB2ENR    (*(volatile uint32_t *)(RCC_BASE + 0x4Cu))

#define GPIOA_BASE     0x48000000u
#define GPIOA_MODER    (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_OTYPER   (*(volatile uint32_t *)(GPIOA_BASE + 0x04u))
#define GPIOA_OSPEEDR  (*(volatile uint32_t *)(GPIOA_BASE + 0x08u))
#define GPIOA_PUPDR    (*(volatile uint32_t *)(GPIOA_BASE + 0x0Cu))
#define GPIOA_IDR      (*(volatile uint32_t *)(GPIOA_BASE + 0x10u))
#define GPIOA_ODR      (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))

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

int main(void)
{
    uint32_t drive_ms   = 0u;
    uint32_t sense_ms   = 0u;
    uint32_t status_ms  = 0u;
    uint32_t led_ms     = 0u;
    uint8_t drive_high   = 0u;
    uint8_t status_high  = 0u;
    uint8_t saw_high     = 0u;
    uint8_t saw_low      = 0u;
    uint8_t loopback_good = 0u;
    uint8_t mb_settled    = 0u;

    RCC_AHB2ENR |= (1u << 0);   /* GPIOAEN */
    (void)RCC_AHB2ENR;

    gpioa_set_output(2u);   /* PA2: signal */
    gpioa_set_output(8u);   /* PA8: drive output → PA6 loopback */
    gpioa_set_input(6u);    /* PA6: sense input */

    GPIOA_ODR &= ~((1u << 2) | (1u << 8));

    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = (1u << 2) | (1u << 0);
    ael_mailbox_init();

    while (1) {
        if ((SYST_CSR & (1u << 16)) == 0u) { continue; }

        drive_ms  += 1u;
        sense_ms  += 1u;
        status_ms += 1u;
        led_ms    += 1u;

        /* Toggle PA8 every 5ms */
        if (drive_ms >= 5u) {
            drive_ms = 0u;
            drive_high ^= 1u;
            if (drive_high != 0u) {
                GPIOA_ODR |= (1u << 8);
            } else {
                GPIOA_ODR &= ~(1u << 8);
            }
        }

        /* Sample PA6 IDR continuously */
        if ((GPIOA_IDR & (1u << 6)) != 0u) {
            saw_high = 1u;
        } else {
            saw_low = 1u;
        }

        /* Evaluate every 100ms: expect both levels seen */
        if (sense_ms >= 100u) {
            loopback_good = (uint8_t)(saw_high != 0u && saw_low != 0u);
            saw_high = 0u;
            saw_low  = 0u;
            sense_ms = 0u;
            if (mb_settled == 0u) {
                if (loopback_good != 0u) { ael_mailbox_pass(); }
                else { ael_mailbox_fail(0xE001u, 0u); }
                mb_settled = 1u;
            }
        }

        if (status_ms >= 5u) {
            status_ms = 0u;
            status_high ^= 1u;
            if (loopback_good != 0u && status_high != 0u) {
                GPIOA_ODR |= (1u << 2);
            } else {
                GPIOA_ODR &= ~(1u << 2);
            }
        }

        /* PA8 is the loopback drive output — LED blinks at drive rate (100Hz), skip separate toggle */
        (void)led_ms;
    }
}
