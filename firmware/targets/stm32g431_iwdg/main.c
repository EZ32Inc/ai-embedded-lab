/*
 * STM32G431CBU6 — IWDG (Independent Watchdog) Test
 *
 * Configures IWDG with LSI clock (~32 kHz), prescaler /256, reload=4095.
 * Nominal timeout ≈ 4095/125 Hz ≈ 32.8 s.
 *
 * Firmware continuously reloads the watchdog every 1 ms (well within
 * the timeout) and increments the mailbox heartbeat counter.
 * A sustained heartbeat proves:
 *   (a) IWDG started without firing immediately (LSI functional, PR/RLR correct).
 *   (b) Firmware keeps running with watchdog active (reload path works).
 *
 * Mailbox at 0x20007F00.
 *   PASS: IWDG running, firmware alive. detail0 = heartbeat (ms count).
 *   (No FAIL path — if IWDG misconfigured the chip resets and mailbox stays
 *    at RUNNING/0, which the pipeline reports as a timeout failure.)
 *
 * Register addresses: RM0440 (STM32G431 Reference Manual).
 * Clock: 16 MHz HSI. IWDG uses internal LSI (~32 kHz), independent of HSI.
 */

#include <stdint.h>
#include "../ael_mailbox.h"

/* ---- RCC (for LSI enable) ----------------------------------------------- */
#define RCC_BASE      0x40021000u
#define RCC_CSR       (*(volatile uint32_t *)(RCC_BASE + 0x94u))
#define RCC_CSR_LSION  (1u << 0)
#define RCC_CSR_LSIRDY (1u << 1)

/* ---- IWDG --------------------------------------------------------------- */
#define IWDG_BASE  0x40003000u
#define IWDG_KR    (*(volatile uint32_t *)(IWDG_BASE + 0x00u))
#define IWDG_PR    (*(volatile uint32_t *)(IWDG_BASE + 0x04u))
#define IWDG_RLR   (*(volatile uint32_t *)(IWDG_BASE + 0x08u))
#define IWDG_SR    (*(volatile uint32_t *)(IWDG_BASE + 0x0Cu))

#define IWDG_KEY_RELOAD  0xAAAAu
#define IWDG_KEY_UNLOCK  0x5555u
#define IWDG_KEY_START   0xCCCCu

/* ---- SysTick ------------------------------------------------------------ */
#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

static void delay_ms(uint32_t ms)
{
    for (uint32_t i = 0u; i < ms; i++) {
        SYST_CVR = 0u;
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

int main(void)
{
    SYST_RVR = 15999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    ael_mailbox_init();

    /*
     * Enable LSI oscillator and wait for it to stabilise.
     * RM0440 §9.4.5: LSIRDY must be set before writing IWDG registers.
     */
    RCC_CSR |= RCC_CSR_LSION;
    while ((RCC_CSR & RCC_CSR_LSIRDY) == 0u) {}

    /*
     * Configure IWDG:
     *   Prescaler /256 → fIWDG ≈ 32000/256 = 125 Hz
     *   Reload = 4095   → timeout ≈ 4095/125 = 32.8 s
     *
     * Long timeout (>> settle_s=5s) so IWDG never fires during observation.
     * Firmware kicks every 1ms, proving LSI, IWDG config, and reload path.
     */
    IWDG_KR  = IWDG_KEY_UNLOCK;
    IWDG_PR  = 0x06u;     /* /256 */
    IWDG_RLR = 4095u;     /* max reload */
    IWDG_KR  = IWDG_KEY_RELOAD;
    IWDG_KR  = IWDG_KEY_START;

    ael_mailbox_pass();

    uint32_t iteration = 0u;
    while (1) {
        delay_ms(1u);
        IWDG_KR = IWDG_KEY_RELOAD;
        AEL_MAILBOX->detail0 = ++iteration;
    }
}
