#include "ch32v30x.h"

static void delay_ms(uint32_t ms)
{
    /* ~96 MHz: rough busy-wait (~9600 cycles/ms) */
    for (uint32_t i = 0; i < ms * 9600; i++)
        __asm__("nop");
}

int main(void)
{
    /* Enable GPIOC clock. */
    RCC->APB2PCENR |= RCC_APB2Periph_GPIOC;

    /* PC2: output push-pull 2 MHz (CFGLR bits [11:8] = 0x2). */
    GPIOC->CFGLR &= ~(0xFu << 8);
    GPIOC->CFGLR |=  (0x2u << 8);

    while (1) {
        GPIOC->BSHR = (1u << 2);
        delay_ms(500);
        GPIOC->BSHR = (1u << 18);
        delay_ms(500);
    }
}
