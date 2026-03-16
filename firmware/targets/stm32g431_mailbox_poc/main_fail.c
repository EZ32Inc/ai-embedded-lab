#include <stdint.h>

/* Same mailbox layout as main.c — forced FAIL variant for PoC testing */

#define MAILBOX_MAGIC   0xAE100001u
#define STATUS_RUNNING  1u
#define STATUS_FAIL     3u

typedef struct {
    uint32_t magic;
    uint32_t status;
    uint32_t error_code;
    uint32_t detail0;
} ael_mailbox_t;

#define MAILBOX  ((volatile ael_mailbox_t *)0x20007F00u)

#define RCC_AHB2ENR  (*(volatile uint32_t *)(0x40021000u + 0x4Cu))
#define GPIOA_MODER  (*(volatile uint32_t *)(0x48000000u + 0x00u))
#define GPIOA_ODR    (*(volatile uint32_t *)(0x48000000u + 0x14u))
#define SYST_CSR     (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR     (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR     (*(volatile uint32_t *)0xE000E018u)

static void delay_ticks(uint32_t n) {
    for (volatile uint32_t i = 0u; i < n; i++)
        while ((SYST_CSR & (1u << 16)) == 0u) {}
}

int main(void) {
    RCC_AHB2ENR |= 1u;
    (void)RCC_AHB2ENR;
    GPIOA_MODER &= ~(0x3u << 16);
    GPIOA_MODER |=  (0x1u << 16);
    GPIOA_ODR   &= ~(1u << 8);
    SYST_RVR = 15999u; SYST_CVR = 0u; SYST_CSR = (1u << 2) | (1u << 0);

    /* Write RUNNING */
    MAILBOX->magic      = MAILBOX_MAGIC;
    MAILBOX->error_code = 0u;
    MAILBOX->detail0    = 0u;
    MAILBOX->status     = STATUS_RUNNING;

    delay_ticks(250u);   /* ~500ms */

    /* Forced FAIL: error_code=0xDEAD0001, detail0=0xCAFE */
    MAILBOX->error_code = 0xDEAD0001u;
    MAILBOX->detail0    = 0x0000CAFEu;
    MAILBOX->status     = STATUS_FAIL;   /* last */

    /* Rapid LED blink = FAIL indicator */
    while (1) {
        GPIOA_ODR ^= (1u << 8);
        delay_ticks(50u);
    }
}
