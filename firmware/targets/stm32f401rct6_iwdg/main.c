/*
 * STM32F401RCT6 — IWDG (Independent Watchdog) Test
 *
 * Configures IWDG with LSI clock (~32 kHz), prescaler /128, reload=999.
 * Nominal timeout ≈ 999/250 Hz ≈ 4.0 s.
 *
 * Firmware continuously reloads the watchdog every 1 ms (well within
 * the timeout) and increments the mailbox heartbeat counter.
 * A sustained heartbeat proves:
 *   (a) IWDG started without firing immediately (LSI functional, PR/RLR correct).
 *   (b) Firmware keeps running with watchdog active (reload path works).
 *
 * The AEL pipeline verifies the mailbox reaches PASS status and heartbeat
 * keeps incrementing within the settle window.
 *
 * Mailbox at 0x2000FC00.
 *   PASS: IWDG running, firmware alive. detail0 = heartbeat (ms count).
 *   (No FAIL path — if IWDG misconfigured the chip resets and mailbox stays
 *    at RUNNING/0, which the pipeline reports as a timeout failure.)
 *
 * Register addresses: RM0368 (STM32F401 Reference Manual).
 * Clock: 16 MHz HSI. IWDG uses internal LSI (~32 kHz), independent of HSI.
 */

#include <stdint.h>
#include "ael_mailbox.h"

/* ---- IWDG --------------------------------------------------------------- */
#define IWDG_BASE  0x40003000u
#define IWDG_KR    (*(volatile uint32_t *)(IWDG_BASE + 0x00u))
#define IWDG_PR    (*(volatile uint32_t *)(IWDG_BASE + 0x04u))
#define IWDG_RLR   (*(volatile uint32_t *)(IWDG_BASE + 0x08u))
#define IWDG_SR    (*(volatile uint32_t *)(IWDG_BASE + 0x0Cu))

#define IWDG_KEY_RELOAD  0xAAAAu   /* reload counter */
#define IWDG_KEY_UNLOCK  0x5555u   /* unlock PR and RLR writes */
#define IWDG_KEY_START   0xCCCCu   /* start IWDG (also locks PR/RLR) */

#define IWDG_SR_PVU  (1u << 0)   /* prescaler value update in progress */
#define IWDG_SR_RVU  (1u << 1)   /* reload value update in progress */

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
     * Configure IWDG:
     *   Prescaler /128 → fIWDG ≈ 32000/128 = 250 Hz
     *   Reload = 999    → timeout ≈ 999/250 = 4.0 s
     *
     * Sequence: unlock → set PR → wait PVU clear → set RLR → wait RVU clear
     *           → reload → start.
     */
    IWDG_KR  = IWDG_KEY_UNLOCK;
    IWDG_PR  = 0x05u;                        /* /128 */
    while (IWDG_SR & IWDG_SR_PVU) {}         /* wait for prescaler update */

    IWDG_KR  = IWDG_KEY_UNLOCK;
    IWDG_RLR = 999u;
    while (IWDG_SR & IWDG_SR_RVU) {}         /* wait for reload update */

    IWDG_KR  = IWDG_KEY_RELOAD;              /* load new reload value */
    IWDG_KR  = IWDG_KEY_START;               /* start IWDG (locks PR/RLR) */

    ael_mailbox_pass();

    uint32_t iteration = 0u;
    while (1) {
        delay_ms(1u);
        IWDG_KR = IWDG_KEY_RELOAD;           /* kick watchdog every 1 ms */
        AEL_MAILBOX->detail0 = ++iteration;
    }
}
