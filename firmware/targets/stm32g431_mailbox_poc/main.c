#include <stdint.h>

/*
 * AEL Debug Mailbox Proof-of-Concept — STM32G431CBU6
 *
 * Mailbox placed at 0x20007F00 (SRAM end - 256 bytes).
 * SRAM: 0x20000000-0x20007FFF (32 KB); stack grows down from 0x20008000.
 * Test firmware stack usage is trivial (<128 bytes), so 0x20007F00 is safe.
 *
 * Sequence:
 *   1. Write magic + STATUS_RUNNING
 *   2. Blink PA8 LED 3 times to show the MCU is alive
 *   3. Run a trivial self-check (1+1==2)
 *   4. Write STATUS_PASS or STATUS_FAIL
 *   5. Spin forever — ready for GDB mailbox read
 *
 * To read the mailbox via GDB:
 *   arm-none-eabi-gdb --batch \
 *     -ex "set pagination off" \
 *     -ex "target remote 192.168.2.62:4242" \
 *     -ex "monitor a" \
 *     -ex "attach 1" \
 *     -ex "x/4xw 0x20007F00" \
 *     -ex "detach" -ex "quit"
 *
 * Expected output (pass):
 *   0x20007f00: 0xae100001  0x00000002  0x00000000  0x00000000
 *               magic       STATUS_PASS error=0     detail=0
 */

/* ---- Mailbox ------------------------------------------------------------ */

#define MAILBOX_MAGIC   0xAE100001u
#define STATUS_EMPTY    0u
#define STATUS_RUNNING  1u
#define STATUS_PASS     2u
#define STATUS_FAIL     3u

typedef struct {
    uint32_t magic;
    uint32_t status;
    uint32_t error_code;
    uint32_t detail0;
} ael_mailbox_t;

#define MAILBOX  ((volatile ael_mailbox_t *)0x20007F00u)

static void mailbox_init(void) {
    MAILBOX->magic      = MAILBOX_MAGIC;
    MAILBOX->error_code = 0u;
    MAILBOX->detail0    = 0u;
    MAILBOX->status     = STATUS_RUNNING;   /* write status last */
}

static void mailbox_pass(void) {
    MAILBOX->status = STATUS_PASS;          /* write status last */
}

static void mailbox_fail(uint32_t error_code, uint32_t detail) {
    MAILBOX->error_code = error_code;
    MAILBOX->detail0    = detail;
    MAILBOX->status     = STATUS_FAIL;      /* write status last */
}

/* ---- GPIO (PA8 LED) ----------------------------------------------------- */

#define RCC_BASE      0x40021000u
#define RCC_AHB2ENR   (*(volatile uint32_t *)(RCC_BASE + 0x4Cu))
#define GPIOA_BASE    0x48000000u
#define GPIOA_MODER   (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))
#define GPIOA_ODR     (*(volatile uint32_t *)(GPIOA_BASE + 0x14u))

/* ---- SysTick ------------------------------------------------------------ */

#define SYST_CSR  (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR  (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR  (*(volatile uint32_t *)0xE000E018u)

static void delay_ticks(uint32_t ticks) {
    for (volatile uint32_t i = 0u; i < ticks; i++) {
        while ((SYST_CSR & (1u << 16)) == 0u) {}
    }
}

/* ---- Self-check --------------------------------------------------------- */

/*
 * Trivial arithmetic check.
 * Returns 0 = pass, non-zero error code = fail.
 */
static uint32_t self_check(void) {
    volatile uint32_t a = 1u;
    volatile uint32_t b = 1u;
    if (a + b != 2u) { return 0xE001u; }  /* basic arithmetic fail */
    if (a * b != 1u) { return 0xE002u; }
    return 0u;
}

/* ---- Main --------------------------------------------------------------- */

int main(void) {
    /* Enable GPIOA clock */
    RCC_AHB2ENR |= (1u << 0);
    (void)RCC_AHB2ENR;

    /* PA8 output push-pull */
    GPIOA_MODER &= ~(0x3u << 16);
    GPIOA_MODER |=  (0x1u << 16);
    GPIOA_ODR   &= ~(1u << 8);

    /* SysTick at ~500 Hz (known effective rate on this unit) */
    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = (1u << 2) | (1u << 0);

    /* Signal MCU alive: 3 LED blinks before writing mailbox */
    for (uint32_t i = 0u; i < 3u; i++) {
        GPIOA_ODR |=  (1u << 8);
        delay_ticks(250u);   /* ~500ms on */
        GPIOA_ODR &= ~(1u << 8);
        delay_ticks(250u);   /* ~500ms off */
    }

    /* Write RUNNING into mailbox */
    mailbox_init();

    /* Run self-check */
    uint32_t err = self_check();

    if (err == 0u) {
        mailbox_pass();
        /* Steady LED = PASS */
        GPIOA_ODR |= (1u << 8);
    } else {
        mailbox_fail(err, 0u);
        /* Rapid blink = FAIL */
        while (1) {
            GPIOA_ODR ^= (1u << 8);
            delay_ticks(50u);
        }
    }

    /* Spin here — GDB can now attach and read mailbox at 0x20007F00 */
    while (1) {}
}
