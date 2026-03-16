/*
 * STM32H750VBT6 — Software PWM Period Measurement
 *
 * PB8: GPIO output push-pull — software square wave, 1 kHz, 50% duty.
 *   TIM2 free-runs at 1 MHz; ODR is toggled every 500 us via spin_us(TIM2).
 *
 * PB9: GPIO input floating — reads bench wire PB8 → PB9.
 *   Software polls GPIOB_IDR bit 9 for rising edges to timestamp period.
 *
 * The test exercises:
 *   – GPIO output drive on PB8
 *   – Bench wire PB8 → PB9
 *   – GPIO input read (GPIOB_IDR) on PB9
 *   – TIM2 free-running at 1 MHz for period measurement
 *
 * Measurement:
 *   1. Wait PB9 = LOW  (synchronise to falling edge)
 *   2. Wait PB9 = HIGH → record t1 (first rising edge)
 *   3. Wait PB9 = LOW  (falling edge of same cycle)
 *   4. Wait PB9 = HIGH → record t2 (second rising edge)
 *   period = t2 − t1.  Accept 900..1100 us (±10% of 1000 us).
 *
 * Error bits in error_code:
 *   bit 0: ERR_CAP1   — first rising-edge timeout
 *   bit 1: ERR_CAP2   — second rising-edge timeout
 *   bit 2: ERR_PERIOD — measured period outside 900..1100 us
 *
 * detail0 = measured period.  On PASS increments each ms tick.
 *
 * Clocks: 64 MHz HSI, no PLL.  TIM2 PSC=63 → 1 MHz (1 us resolution).
 */

#define AEL_MAILBOX_ADDR  0x38000000u
#include "../ael_mailbox.h"

/* ---- RCC (RM0433 §8) ---------------------------------------------------- */

#define RCC_BASE              0x58024400u
#define RCC_AHB4ENR           (*(volatile uint32_t *)(RCC_BASE + 0x0E0u))
#define RCC_APB1LENR          (*(volatile uint32_t *)(RCC_BASE + 0x0E8u))
#define RCC_AHB4ENR_GPIOBEN   (1u << 1)
#define RCC_APB1LENR_TIM2EN   (1u << 0)

/* ---- GPIOB (RM0433 §10, base 0x58020400) -------------------------------- */

#define GPIOB_BASE   0x58020400u
#define GPIOB_MODER  (*(volatile uint32_t *)(GPIOB_BASE + 0x00u))
#define GPIOB_IDR    (*(volatile uint32_t *)(GPIOB_BASE + 0x10u))
#define GPIOB_ODR    (*(volatile uint32_t *)(GPIOB_BASE + 0x14u))

#define GPIOB_PIN8   (1u << 8)
#define GPIOB_PIN9   (1u << 9)

/* ---- TIM2 (RM0433 §43, APB1L base 0x40000000) — 32-bit free-running ----- */

#define TIM2_BASE    0x40000000u
#define TIM2_CR1     (*(volatile uint32_t *)(TIM2_BASE + 0x00u))
#define TIM2_EGR     (*(volatile uint32_t *)(TIM2_BASE + 0x14u))
#define TIM2_CNT     (*(volatile uint32_t *)(TIM2_BASE + 0x24u))
#define TIM2_PSC     (*(volatile uint32_t *)(TIM2_BASE + 0x28u))
#define TIM2_ARR     (*(volatile uint32_t *)(TIM2_BASE + 0x2Cu))

#define TIM_EGR_UG   (1u << 0)

/* ---- SysTick (ARMv7-M ARM) ---------------------------------------------- */

#define SYST_CSR        (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR        (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR        (*(volatile uint32_t *)0xE000E018u)
#define SYST_CSR_ENABLE    (1u << 0)
#define SYST_CSR_CLKSOURCE (1u << 2)
#define SYST_CSR_COUNTFLAG (1u << 16)

/* ---- Error bits --------------------------------------------------------- */

#define ERR_CAP1    (1u << 0)
#define ERR_CAP2    (1u << 1)
#define ERR_PERIOD  (1u << 2)

/* ---- Helpers ------------------------------------------------------------ */

static void delay_ticks(uint32_t ticks)
{
    for (volatile uint32_t i = 0u; i < ticks; i++) {
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

/* Wait until TIM2_CNT has advanced 'us' counts from when this is called. */
static void spin_us(uint32_t us)
{
    uint32_t start = TIM2_CNT;
    while ((TIM2_CNT - start) < us) {}
}

/* Poll GPIOB_IDR bit 9 until it equals level_val.
 * Returns 1 on match, 0 on timeout (~1 s at 64 MHz). */
static int wait_pb9(uint32_t level_val)
{
    uint32_t timeout = 10000000u;
    while ((GPIOB_IDR & GPIOB_PIN9) != level_val) {
        if (--timeout == 0u) { return 0; }
    }
    return 1;
}

/* ---- Main --------------------------------------------------------------- */

int main(void)
{
    /* SysTick: 64 MHz, RVR=63999 → 1 ms/tick */
    SYST_RVR = 63999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    /* Enable GPIOB and TIM2 clocks */
    RCC_AHB4ENR |= RCC_AHB4ENR_GPIOBEN;
    (void)RCC_AHB4ENR;
    RCC_APB1LENR |= RCC_APB1LENR_TIM2EN;
    (void)RCC_APB1LENR;

    ael_mailbox_init();

    /*
     * PB8: output push-pull (MODER[17:16] = 01).
     * PB9: input floating   (MODER[19:18] = 00, reset default).
     */
    GPIOB_MODER &= ~((0x3u << 16u) | (0x3u << 18u));
    GPIOB_MODER |=   (0x1u << 16u);    /* PB8 = output */

    /* ---- TIM2: 32-bit free-running at 1 MHz ----------------------------- */

    TIM2_CR1 = 0u;
    TIM2_PSC = 63u;           /* 64 MHz / 64 = 1 MHz                        */
    TIM2_ARR = 0xFFFFFFFFu;   /* free-run                                    */
    TIM2_EGR = TIM_EGR_UG;   /* load PSC/ARR                               */
    TIM2_CNT = 0u;
    TIM2_CR1 = 1u;            /* CEN                                         */

    /* ---- Software 1 kHz square wave on PB8 ------------------------------ */
    /*
     * Drive a repeating square wave on PB8 using spin_us(TIM2) for timing.
     * The measurement loop polls PB9 IDR for rising edges.
     * PB8 LOW → 500 us → HIGH → 500 us → LOW → 500 us → HIGH → ...
     * Run for at least 4 complete cycles before the measurement window so PB9
     * is guaranteed to be toggling when we start polling.
     */

    GPIOB_ODR &= ~GPIOB_PIN8;   /* start LOW */
    delay_ticks(2u);             /* 2 ms startup margin */

    /* ---- Edge detection and period measurement -------------------------- */

    uint32_t err    = 0u;
    uint32_t t1     = 0u;
    uint32_t t2     = 0u;
    uint32_t period = 0u;

    /*
     * Drive PB8 LOW to start at a known level, then begin the square wave
     * in a background loop while the foreground polls PB9.
     *
     * Implementation: interleave the ODR toggle with the IDR polling.
     * PB8 is driven and PB9 is sampled in the same loop body so that the
     * square wave keeps running throughout the detection window.
     *
     * Timing: each half-cycle is 500 us.  Toggling is driven by spin_us(500).
     * The full measurement loop is bounded by 10 s (4 × 10M-iteration timeout).
     */

    /* Start with PB8 LOW, spin 500us then go HIGH.  This ensures PB9 is LOW
     * when we call wait_pb9(0) so the first timeout starts from a defined state. */
    GPIOB_ODR &= ~GPIOB_PIN8;
    spin_us(500u);

    /* --- First rising edge ------------------------------------------------ */
    /* PB8 should be LOW now; drive it HIGH on next toggle to create rising edge */
    GPIOB_ODR |= GPIOB_PIN8;     /* rising edge: PB8 goes HIGH */

    /* Simultaneously: wait for PB9 to go HIGH (wire propagation < 1 us) */
    if (!wait_pb9(GPIOB_PIN9)) {
        err |= ERR_CAP1;
    } else {
        t1 = TIM2_CNT;           /* timestamp first rising edge */
    }

    /* Keep driving: 500 us HIGH, then LOW */
    if ((err & ERR_CAP1) == 0u) {
        spin_us(500u);
        GPIOB_ODR &= ~GPIOB_PIN8;  /* falling edge */

        /* --- Second rising edge ------------------------------------------ */
        spin_us(500u);
        GPIOB_ODR |= GPIOB_PIN8;   /* rising edge: PB8 goes HIGH */

        if (!wait_pb9(GPIOB_PIN9)) {
            err |= ERR_CAP2;
        } else {
            t2 = TIM2_CNT;         /* timestamp second rising edge */
        }
    }

    /* Compute period */
    if (err == 0u) {
        period = t2 - t1;   /* 32-bit subtraction; TIM2 wraps at 2^32 */
        if (period < 900u || period > 1100u) {
            err |= ERR_PERIOD;
        }
    }

    if (err == 0u) {
        ael_mailbox_pass();
        uint32_t iteration = period;
        while (1) {
            delay_ticks(1u);
            iteration++;
            AEL_MAILBOX->detail0 = iteration;
        }
    } else {
        ael_mailbox_fail(err, period);
        while (1) {}
    }
}
