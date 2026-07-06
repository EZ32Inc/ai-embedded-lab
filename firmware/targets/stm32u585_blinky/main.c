#include <stdint.h>
#include "../ael_mailbox.h"

/* ------------------------------------------------------------------ *
 * STM32U585CIU6 — LED Blinky (PC13, active-low)
 *
 * Clock: MSI default at 4 MHz after reset (no PLL config needed).
 *
 * Register map verified from stm32u585xx.h (ST official CMSIS header):
 *   https://github.com/STMicroelectronics/cmsis_device_u5
 *
 *   RCC base      : 0x46020C00
 *   RCC_AHB2ENR1  : RCC + 0x08C   bit2 = GPIOCEN
 *
 *   GPIOC base    : 0x42020800
 *   GPIOC_MODER   : +0x00   bits[27:26] = 01 → output
 *   GPIOC_OTYPER  : +0x04   bit13 = 0 → push-pull (default)
 *   GPIOC_BSRR    : +0x18   bit13 = SET high (LED off)
 *                            bit29 = RESET low (LED on)
 * ------------------------------------------------------------------ */

#define RCC_BASE         0x46020C00u
#define RCC_AHB2ENR1     (*(volatile uint32_t *)(RCC_BASE + 0x08Cu))  /* stm32u585xx.h: RCC_TypeDef offset 0x8C */

#define GPIOC_BASE       0x42020800u
#define GPIOC_MODER      (*(volatile uint32_t *)(GPIOC_BASE + 0x00u))
#define GPIOC_BSRR       (*(volatile uint32_t *)(GPIOC_BASE + 0x18u))

/* ~250 ms at 4 MHz MSI (loop body ≈ 4 cycles) */
#define DELAY_HALF_S     125000u

static void delay(uint32_t n) {
    for (volatile uint32_t i = 0u; i < n; i++) {}
}

int main(void) {
    /* Enable GPIOC clock */
    RCC_AHB2ENR1 |= (1u << 2);

    /* PC13: clear MODER[27:26] (analog default), set to 01 (output) */
    GPIOC_MODER &= ~(3u << 26);
    GPIOC_MODER |=  (1u << 26);

    /* Signal AEL: firmware is running */
    ael_mailbox_init();

    /* Blink PC13 forever: LED ON (low) -> 250ms -> LED OFF (high) -> 250ms */
    while (1) {
        GPIOC_BSRR = (1u << 29);   /* reset PC13 low -> LED ON */
        delay(DELAY_HALF_S);
        GPIOC_BSRR = (1u << 13);   /* set PC13 high -> LED OFF */
        delay(DELAY_HALF_S);

        /* Keep reporting PASS on every cycle */
        ael_mailbox_pass();
    }

    return 0;
}
