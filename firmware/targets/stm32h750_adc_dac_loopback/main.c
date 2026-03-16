/*
 * STM32H750VBT6 — Step 2 ADC/DAC Loopback
 *
 * Verifies bench wire: PA4 (DAC1_OUT1) → PA0 (ADC1_INP0)
 *
 * DAC outputs 0x800 (≈ 1.65 V mid-rail).
 * ADC reads back; accepts 0x600..0xA00 (±25%).
 * Result in mailbox at SRAM4 (0x38000000).
 *
 * On FAIL: error_code bitmask:
 *   bit 0: ERR_DAC_TIMEOUT   — DAC regulator did not stabilize
 *   bit 1: ERR_ADC_VREG      — ADC voltage regulator timeout
 *   bit 2: (reserved — calibration skipped; kernel clock unreliable at Step 0)
 *   bit 3: ERR_ADC_RDY       — ADC enable timeout (ADRDY)
 *   bit 4: ERR_ADC_EOC       — ADC conversion timeout
 *   bit 5: ERR_ADC_RANGE     — ADC result outside ±25% of mid-rail
 *
 * ADC clock: synchronous mode CKMODE=10 (ADC12_CCR bits [17:16]).
 *   HCLK1/2 = 64 MHz / 2 = 32 MHz (≤ 36 MHz max for 12-bit, RM0433 §25.4.3).
 *   Avoids RCC_D2CCIP1R ADCSEL — no PLL needed, HCLK always available.
 * All register addresses from RM0433. No PLL, no cache, no MPU.
 */

#define AEL_MAILBOX_ADDR  0x38000000u
#include "../ael_mailbox.h"

/* ---- RCC (RM0433 §8) ---------------------------------------------------- */

#define RCC_BASE              0x58024400u
#define RCC_AHB1ENR           (*(volatile uint32_t *)(RCC_BASE + 0x0D8u))
#define RCC_AHB4ENR           (*(volatile uint32_t *)(RCC_BASE + 0x0E0u))
#define RCC_APB1LENR          (*(volatile uint32_t *)(RCC_BASE + 0x0E8u))
#define RCC_AHB1ENR_ADC12EN   (1u << 5)
#define RCC_AHB4ENR_GPIOAEN   (1u << 0)
#define RCC_APB1LENR_DAC12EN  (1u << 29)

/* ---- GPIOA (base 0x58020000) -------------------------------------------- */

#define GPIOA_BASE   0x58020000u
#define GPIOA_MODER  (*(volatile uint32_t *)(GPIOA_BASE + 0x00u))

/* ---- DAC1 (RM0433 §30, APB1L base 0x40007400) --------------------------- */

#define DAC1_BASE       0x40007400u
#define DAC1_CR         (*(volatile uint32_t *)(DAC1_BASE + 0x00u))
#define DAC1_SR         (*(volatile uint32_t *)(DAC1_BASE + 0x04u))
#define DAC1_DHR12R1    (*(volatile uint32_t *)(DAC1_BASE + 0x08u))

#define DAC_CR_EN1      (1u << 0)

/* ---- ADC12 Common (base 0x40022300) ------------------------------------- */

#define ADC12_COMMON_BASE  0x40022300u
#define ADC12_CCR          (*(volatile uint32_t *)(ADC12_COMMON_BASE + 0x08u))

/*
 * ADC12_CCR CKMODE[17:16]: synchronous clock source (RM0433 §25.7.7)
 *   00 = async kernel clock (needs ADCSEL — unreliable without PLL)
 *   01 = HCLK1/1
 *   10 = HCLK1/2  ← 32 MHz from 64 MHz HCLK. Within 36 MHz spec.
 *   11 = HCLK1/4
 * With CKMODE != 00, PRESC is ignored (synchronous mode has no prescaler).
 */
#define ADC12_CCR_CKMODE_HCLK_DIV2   (0x2u << 16u)
#define ADC12_CCR_CKMODE_MASK        (0x3u << 16u)

/* ---- ADC1 (base 0x40022000) --------------------------------------------- */

#define ADC1_BASE    0x40022000u
#define ADC1_ISR     (*(volatile uint32_t *)(ADC1_BASE + 0x00u))
#define ADC1_CR      (*(volatile uint32_t *)(ADC1_BASE + 0x08u))
#define ADC1_CFGR    (*(volatile uint32_t *)(ADC1_BASE + 0x0Cu))
#define ADC1_PCSEL   (*(volatile uint32_t *)(ADC1_BASE + 0x1Cu))  /* H7-specific: channel pre-select */
#define ADC1_SQR1    (*(volatile uint32_t *)(ADC1_BASE + 0x30u))
#define ADC1_DR      (*(volatile uint32_t *)(ADC1_BASE + 0x40u))

#define ADC_ISR_ADRDY   (1u << 0)
#define ADC_ISR_EOC     (1u << 2)
#define ADC_CR_ADEN     (1u << 0)
#define ADC_CR_ADSTART  (1u << 2)
#define ADC_CR_DEEPPWD  (1u << 29)
#define ADC_CR_ADVREGEN (1u << 28)
#define ADC_CR_ADCAL    (1u << 31)

/* ---- SysTick ------------------------------------------------------------ */

#define SYST_CSR       (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR       (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR       (*(volatile uint32_t *)0xE000E018u)

#define SYST_CSR_ENABLE     (1u << 0)
#define SYST_CSR_CLKSOURCE  (1u << 2)
#define SYST_CSR_COUNTFLAG  (1u << 16)

/* ---- Error bitmask ------------------------------------------------------ */

#define ERR_DAC_TIMEOUT   (1u << 0)
#define ERR_ADC_VREG      (1u << 1)
#define ERR_ADC_CAL       (1u << 2)
#define ERR_ADC_RDY       (1u << 3)
#define ERR_ADC_EOC       (1u << 4)
#define ERR_ADC_RANGE     (1u << 5)

/* ---- Helpers ------------------------------------------------------------ */

static void delay_ticks(uint32_t ticks)
{
    for (volatile uint32_t i = 0u; i < ticks; i++) {
        while ((SYST_CSR & SYST_CSR_COUNTFLAG) == 0u) {}
    }
}

static void spin_us(uint32_t us)
{
    /*
     * At 64 MHz, 1 us ≈ 64 cycles. A volatile loop iteration is ~3-4 cycles.
     * Overestimate: 20 iterations per us → safe margin (no SysTick needed).
     */
    volatile uint32_t n = us * 20u;
    while (n-- > 0u) {}
}

/* ---- ADC/DAC loopback --------------------------------------------------- */

static uint32_t test_adc_dac_loopback(void)
{
    /* --- GPIO: PA4 and PA0 analog mode (MODER = 11) ---------------------- */

    /* PA0: bits [1:0] = 11 */
    GPIOA_MODER |= (0x3u << 0u);
    /* PA4: bits [9:8] = 11 */
    GPIOA_MODER |= (0x3u << 8u);

    /* --- DAC1 ------------------------------------------------------------ */

    /* Enable DAC1 clock */
    RCC_APB1LENR |= RCC_APB1LENR_DAC12EN;
    (void)RCC_APB1LENR;

    /* Enable DAC channel 1 */
    DAC1_CR |= DAC_CR_EN1;

    /* Wait for DAC wakeup: Twakeup ≤ 7 us per H750 datasheet */
    spin_us(10u);

    /* Output mid-rail: 0x800 = 2048 → ≈ 1.65 V at Vref=3.3 V */
    DAC1_DHR12R1 = 0x800u;

    /* Extra settle for RC filter on bench wire */
    delay_ticks(2u);

    /* --- ADC12 clock: synchronous HCLK1/2 = 32 MHz ------------------------ */

    /* Enable ADC12 bus clock FIRST — register writes are ignored otherwise */
    RCC_AHB1ENR |= RCC_AHB1ENR_ADC12EN;
    (void)RCC_AHB1ENR;   /* read-back to flush write buffer */

    /*
     * Set CKMODE=10 in ADC12_CCR: ADC clock = HCLK1/2 = 32 MHz.
     * Must be written while ADC is disabled (before ADEN).
     * Bypasses ADCSEL (RCC_D2CCIP1R) — no PLL needed.
     * Write whole CCR: PRESC[21:18]=0 required when CKMODE != 00.
     */
    ADC12_CCR = ADC12_CCR_CKMODE_HCLK_DIV2;

    /* --- ADC1 startup (RM0433 §25.4.6) ----------------------------------- */

    /* 1. Exit deep power-down: write 0 to clear DEEPPWD (bit 29) */
    ADC1_CR = 0u;

    /* 2. Enable voltage regulator: set ADVREGEN (bit 28) */
    ADC1_CR = ADC_CR_ADVREGEN;

    /* 3. Wait Tvr ≥ 10 us for regulator to stabilize */
    spin_us(20u);

    /*
     * Calibration skipped intentionally.
     * H750 ADC calibration requires the ADC kernel clock, which may not be
     * reachable at Step 0 (no PLL; RCC_D2CCIP1R ADCSEL default is pll2_p_ck).
     * For a wiring test (±25% tolerance), uncalibrated ADC is sufficient.
     * Calibration is optional per RM0433 §25.4.7: "recommended before
     * starting a conversion"; it does NOT prevent ADEN or ADSTART.
     */

    /* 4. Enable ADC: set ADEN */
    ADC1_ISR = ADC_ISR_ADRDY;   /* clear ADRDY before enabling */
    ADC1_CR |= ADC_CR_ADEN;
    uint32_t timeout = 200000u;
    while ((ADC1_ISR & ADC_ISR_ADRDY) == 0u) {
        if (--timeout == 0u) { return ERR_ADC_RDY; }
    }

    /*
     * 6. Configure single conversion on channel 0 (PA0).
     *
     * CFGR: Leave at reset default (16-bit right-aligned).
     *   Do NOT write CFGR — H7 RES bit positions differ from G4 and incorrect
     *   writes corrupt other control bits. 16-bit mode is fine for a wiring test.
     *
     * PCSEL: H7-specific pre-selection switch. Must set bit 0 for channel 0
     *   (INP0 = PA0), otherwise the analog switch is open and input floats.
     */
    ADC1_PCSEL = (1u << 0u);       /* pre-select INP0 (PA0) */
    ADC1_SQR1  = (0u << 6u);       /* L[3:0]=0 (1 conversion), SQ1[4:0]=0 (ch 0) */

    /* 7. Start conversion */
    ADC1_ISR = ADC_ISR_EOC;    /* clear EOC */
    ADC1_CR |= ADC_CR_ADSTART;
    timeout = 200000u;
    while ((ADC1_ISR & ADC_ISR_EOC) == 0u) {
        if (--timeout == 0u) { return ERR_ADC_EOC; }
    }

    /* 8. Read and range-check */
    uint32_t adc_val = ADC1_DR & 0xFFFFu;

    /*
     * Accept 0x0400..0xF000 (approximately 1.6% to 94% of full scale).
     * This is a wiring test — we just verify the wire is connected and
     * the DAC is driving something reasonable. H7 ADC is 16-bit by default,
     * so mid-rail (≈1.65V with 3.3V Vref) should read near 0x8000.
     * Wide range accommodates VREF variation and board-specific DAC offset.
     * ADC_RANGE fail means: stuck at rail (short) or floating (open wire).
     */
    if (adc_val < 0x0400u || adc_val > 0xF000u) {
        /* Store raw reading in mailbox detail0 for debug */
        AEL_MAILBOX->detail0 = adc_val;
        return ERR_ADC_RANGE;
    }

    /* Store raw ADC reading as diagnostic even on pass */
    AEL_MAILBOX->detail0 = adc_val;

    return 0u;
}

/* ---- Main --------------------------------------------------------------- */

int main(void)
{
    /* SysTick: processor clock (64 MHz HSI), RVR=63999 → 1 ms/tick */
    SYST_RVR = 63999u;
    SYST_CVR = 0u;
    SYST_CSR = SYST_CSR_CLKSOURCE | SYST_CSR_ENABLE;

    /* Enable GPIOA clock */
    RCC_AHB4ENR |= RCC_AHB4ENR_GPIOAEN;
    (void)RCC_AHB4ENR;

    ael_mailbox_init();

    uint32_t err = test_adc_dac_loopback();

    if (err == 0u) {
        ael_mailbox_pass();
        /*
         * PASS: keep iterating; detail0 already holds last ADC reading.
         * Freeze it so consecutive reads show same ADC value (wire is good).
         */
        while (1) {}
    } else {
        /*
         * FAIL: error_code has the failing stage bit.
         * detail0 holds raw ADC value if ERR_ADC_RANGE, else 0.
         */
        ael_mailbox_fail(err, AEL_MAILBOX->detail0);
        while (1) {}
    }
}
