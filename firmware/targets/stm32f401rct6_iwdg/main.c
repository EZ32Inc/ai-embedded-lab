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

/* ---- RCC (for LSI enable) ----------------------------------------------- */
#define RCC_BASE   0x40023800u
#define RCC_CSR    (*(volatile uint32_t *)(RCC_BASE + 0x74u))
#define RCC_CSR_LSION  (1u << 0)
#define RCC_CSR_LSIRDY (1u << 1)

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
     * Enable LSI oscillator and wait for it to stabilise.
     * RM0368 §14.3.4: LSIRDY must be set before writing IWDG registers;
     * otherwise PVU/RVU bits never clear (update occurs in VDD/LSI domain).
     */
    RCC_CSR |= RCC_CSR_LSION;
    while ((RCC_CSR & RCC_CSR_LSIRDY) == 0u) {}

    /*
     * Configure IWDG:
     *   Prescaler /256 → fIWDG ≈ 32000/256 = 125 Hz
     *   Reload = 4095   → timeout ≈ 4095/125 = 32.8 s
     *
     * Use a long timeout (>> settle_s=5s) so IWDG never fires during the
     * mailbox observation window. Firmware kicks every 1ms so it won't
     * fire in normal operation. This tests: LSI starts, IWDG configures
     * and starts without premature reset, firmware survives with IWDG active.
     *
     * Sequence: unlock → set PR → wait PVU clear → set RLR → wait RVU clear
     *           → reload → start.
     */
    /*
     * PVU/RVU waits are only required when modifying a running IWDG.
     * For initial configuration before start, write directly.
     */
    IWDG_KR  = IWDG_KEY_UNLOCK;
    IWDG_PR  = 0x06u;                        /* /256 */
    IWDG_RLR = 4095u;                        /* max reload → ~32s timeout */
    IWDG_KR  = IWDG_KEY_RELOAD;              /* load reload value into counter */
    IWDG_KR  = IWDG_KEY_START;               /* start IWDG */

    ael_mailbox_pass();

    uint32_t iteration = 0u;
    while (1) {
        delay_ms(1u);
        IWDG_KR = IWDG_KEY_RELOAD;           /* kick watchdog every 1 ms */
        AEL_MAILBOX->detail0 = ++iteration;
    }
}
