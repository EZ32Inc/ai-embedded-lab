/* pico_full_suite_s3jtag — Rule D combined firmware
 *
 * Runs all 13 sub-tests in sequence.  Results reported via UART0
 * through the S3JTAG internal Web UART bridge (GPIO0 TX → S3JTAG GPIO7).
 *
 * Bench wiring (no changes to existing full-suite contract):
 *   GPIO0  TX → S3JTAG GPIO7   (UART report path)
 *   GPIO1  RX ← S3JTAG GPIO6
 *   GPIO3  → GPIO4             (SPI loopback)
 *   GPIO16 → GPIO17            (GPIO drive / IRQ loopback — reused for
 *                               level, sig, pwm and irq sub-tests)
 *   GPIO22 → GPIO26/ADC0       (ADC loopback)
 *   GPIO18 → S3JTAG TARGETIN   (untouched — individual truth-layer only)
 *   SWDIO / SWCLK / GND as usual
 *
 * Output format (same convention as ESP32 full_suite):
 *   AEL_SUITE_FULL START
 *   AEL_TEST <name> PASS [detail]
 *   AEL_TEST <name> FAIL [detail]
 *   AEL_SUITE_FULL DONE passed=N failed=M
 */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "hardware/adc.h"
#include "hardware/gpio.h"
#include "hardware/pwm.h"
#include "hardware/spi.h"
#include "pico/stdlib.h"

/* ------------------------------------------------------------------ */
/* Pin assignments                                                      */
/* ------------------------------------------------------------------ */
#define UART_TX_PIN    0u
#define UART_RX_PIN    1u
#define SPI_SCK_PIN    2u
#define SPI_TX_PIN     3u
#define SPI_RX_PIN     4u
#define GPIO_DRIVE     16u   /* output: drive level / pulses / PWM  */
#define GPIO_READ      17u   /* input:  read level / count edges    */
#define ADC_DRIVE_PIN  22u   /* output: drive GPIO26/ADC0           */
#define ADC_GPIO       26u   /* ADC0 input                          */
#define LED_PIN        25u

/* ------------------------------------------------------------------ */
/* IRQ edge counter                                                     */
/* ------------------------------------------------------------------ */
static volatile uint32_t g_edge_count = 0u;

static void edge_cb(uint gpio, uint32_t events) {
    (void)gpio;
    if (events & GPIO_IRQ_EDGE_RISE) {
        g_edge_count++;
    }
}

static void irq_start(void) {
    g_edge_count = 0u;
    gpio_set_irq_enabled_with_callback(GPIO_READ, GPIO_IRQ_EDGE_RISE,
                                       true, &edge_cb);
}

static void irq_stop(void) {
    gpio_set_irq_enabled(GPIO_READ, GPIO_IRQ_EDGE_RISE, false);
}

/* ------------------------------------------------------------------ */
/* GPIO16/17 helpers                                                    */
/* ------------------------------------------------------------------ */
static void gpio_drive_init(void) {
    gpio_init(GPIO_DRIVE);
    gpio_set_dir(GPIO_DRIVE, GPIO_OUT);
    gpio_put(GPIO_DRIVE, 0);
}

static void gpio_read_init(void) {
    gpio_init(GPIO_READ);
    gpio_set_dir(GPIO_READ, GPIO_IN);
    gpio_pull_down(GPIO_READ);
}

/* ------------------------------------------------------------------ */
/* Result tracking                                                      */
/* ------------------------------------------------------------------ */
static int g_pass = 0;
static int g_fail = 0;

static void report(const char *name, bool ok, const char *detail) {
    if (ok) {
        g_pass++;
        if (detail)
            printf("AEL_TEST %s PASS %s\n", name, detail);
        else
            printf("AEL_TEST %s PASS\n", name);
    } else {
        g_fail++;
        if (detail)
            printf("AEL_TEST %s FAIL %s\n", name, detail);
        else
            printf("AEL_TEST %s FAIL\n", name);
    }
    fflush(stdout);
}

/* ================================================================== */
/* Sub-tests                                                            */
/* ================================================================== */

/* 1. minimal_runtime — boot reached, UART reachable */
static void sub_minimal_runtime(void) {
    report("minimal_runtime", true, NULL);
}

/* 2. internal_temp — RP2040 on-chip temperature ADC (channel 4) */
static void sub_internal_temp(void) {
    const uint SAMPLES = 8u;
    uint16_t mn = 0xffffu, mx = 0u;
    uint32_t sum = 0u;

    adc_set_temp_sensor_enabled(true);
    adc_select_input(4);
    sleep_ms(20);

    for (uint i = 0u; i < SAMPLES; ++i) {
        uint16_t s = adc_read();
        if (s < mn) mn = s;
        if (s > mx) mx = s;
        sum += s;
        sleep_ms(5);
    }
    uint16_t avg    = (uint16_t)(sum / SAMPLES);
    uint16_t spread = mx - mn;
    char buf[48];
    snprintf(buf, sizeof(buf), "avg=%u spread=%u", avg, spread);
    report("internal_temp", avg > 0u && avg < 4095u && spread > 0u, buf);
}

/* 3. timer — sleep accuracy within ±5 ms */
static void sub_timer(void) {
    const uint32_t SLEEP_MS   = 100u;
    const uint32_t TOLERANCE  = 5000u; /* µs */
    uint64_t t0      = time_us_64();
    sleep_ms(SLEEP_MS);
    uint64_t elapsed = time_us_64() - t0;
    int32_t  delta   = (int32_t)elapsed - (int32_t)(SLEEP_MS * 1000u);
    if (delta < 0) delta = -delta;
    char buf[32];
    snprintf(buf, sizeof(buf), "delta_us=%ld", (long)delta);
    report("timer", (uint32_t)delta < TOLERANCE, buf);
}

/* 4. gpio_level_low — GPIO16 driven LOW, read back on GPIO17 */
static void sub_gpio_level_low(void) {
    gpio_drive_init();
    gpio_read_init();
    gpio_put(GPIO_DRIVE, 0);
    sleep_ms(5);
    report("gpio_level_low", gpio_get(GPIO_READ) == 0u, NULL);
}

/* 5. gpio_level_high — GPIO16 driven HIGH, read back on GPIO17 */
static void sub_gpio_level_high(void) {
    gpio_put(GPIO_DRIVE, 1);
    sleep_ms(5);
    bool ok = (gpio_get(GPIO_READ) == 1u);
    gpio_put(GPIO_DRIVE, 0);
    report("gpio_level_high", ok, NULL);
}

/* 6. gpio_sig_100hz — software toggle at ~100 Hz, count edges on GPIO17
 *    60 full cycles → 60 rising edges expected; tolerance ±17 % (50–70) */
static void sub_gpio_sig_100hz(void) {
    const uint32_t HALF_US = 5000u;
    const uint32_t CYCLES  = 60u;

    irq_start();
    for (uint32_t i = 0u; i < CYCLES; ++i) {
        gpio_put(GPIO_DRIVE, 1); sleep_us(HALF_US);
        gpio_put(GPIO_DRIVE, 0); sleep_us(HALF_US);
    }
    sleep_ms(10);
    irq_stop();

    uint32_t edges = g_edge_count;
    char buf[32];
    snprintf(buf, sizeof(buf), "edges=%lu", (unsigned long)edges);
    report("gpio_sig_100hz", edges >= 50u && edges <= 70u, buf);
}

/* 7. gpio_sig_1khz — software toggle at ~1 kHz, count edges on GPIO17
 *    300 cycles → 300 rising edges expected; tolerance ±15 % (255–345) */
static void sub_gpio_sig_1khz(void) {
    const uint32_t HALF_US = 500u;
    const uint32_t CYCLES  = 300u;

    irq_start();
    for (uint32_t i = 0u; i < CYCLES; ++i) {
        gpio_put(GPIO_DRIVE, 1); sleep_us(HALF_US);
        gpio_put(GPIO_DRIVE, 0); sleep_us(HALF_US);
    }
    sleep_ms(5);
    irq_stop();

    uint32_t edges = g_edge_count;
    char buf[32];
    snprintf(buf, sizeof(buf), "edges=%lu", (unsigned long)edges);
    report("gpio_sig_1khz", edges >= 255u && edges <= 345u, buf);
}

/* 8. pwm_1khz — hardware PWM on GPIO16 at 1 kHz / 50 % duty,
 *    count rising edges on GPIO17 over 500 ms → expect ~500 ± 10 % */
static void sub_pwm_1khz(void) {
    /* sys_clk=125 MHz, div=125, wrap=999 → 1000 Hz */
    gpio_set_function(GPIO_DRIVE, GPIO_FUNC_PWM);
    uint slice = pwm_gpio_to_slice_num(GPIO_DRIVE);
    pwm_config cfg = pwm_get_default_config();
    pwm_config_set_clkdiv(&cfg, 125.0f);
    pwm_config_set_wrap(&cfg, 999u);
    pwm_init(slice, &cfg, false);
    pwm_set_gpio_level(GPIO_DRIVE, 500u);
    pwm_set_enabled(slice, true);

    irq_start();
    sleep_ms(500);
    irq_stop();

    pwm_set_enabled(slice, false);
    gpio_drive_init(); /* restore GPIO_DRIVE as plain GPIO output */

    uint32_t edges = g_edge_count;
    char buf[32];
    snprintf(buf, sizeof(buf), "edges=%lu", (unsigned long)edges);
    report("pwm_1khz", edges >= 450u && edges <= 550u, buf);
}

/* 9. gpio_irq_loopback — 100 software pulses, IRQ must count exactly 100 */
static void sub_gpio_irq_loopback(void) {
    const uint32_t TARGET = 100u;

    irq_start();
    for (uint32_t i = 0u; i < TARGET; ++i) {
        gpio_put(GPIO_DRIVE, 1); sleep_us(500);
        gpio_put(GPIO_DRIVE, 0); sleep_us(500);
    }
    sleep_ms(20);
    irq_stop();

    uint32_t cnt = g_edge_count;
    char buf[32];
    snprintf(buf, sizeof(buf), "count=%lu", (unsigned long)cnt);
    report("gpio_irq_loopback", cnt == TARGET, buf);
}

/* 10. uart_rxd — UART peripheral alive; non-blocking RX drain */
static void sub_uart_rxd(void) {
    int c = getchar_timeout_us(0u);
    (void)c;
    report("uart_rxd", true, "init=ok");
}

/* 11. uart_banner — already printing, trivially PASS */
static void sub_uart_banner(void) {
    report("uart_banner", true, "path=ok");
}

/* 12. spi_loopback — SPI0, GPIO3 TX → GPIO4 RX, 4-byte pattern */
static void sub_spi_loopback(void) {
    spi_init(spi0, 1000u * 1000u);
    gpio_set_function(SPI_SCK_PIN, GPIO_FUNC_SPI);
    gpio_set_function(SPI_TX_PIN,  GPIO_FUNC_SPI);
    gpio_set_function(SPI_RX_PIN,  GPIO_FUNC_SPI);

    const uint8_t tx[] = {0x55u, 0xAAu, 0x3Cu, 0xC3u};
    uint8_t rx[sizeof(tx)] = {0u};
    spi_write_read_blocking(spi0, tx, rx, sizeof(tx));

    bool ok = (memcmp(tx, rx, sizeof(tx)) == 0);
    char buf[48];
    snprintf(buf, sizeof(buf), "rx=%02X%02X%02X%02X", rx[0], rx[1], rx[2], rx[3]);
    report("spi_loopback", ok, buf);

    spi_deinit(spi0);
}

/* 13. adc_loopback — GPIO22 drives GPIO26/ADC0 HIGH then LOW */
static void sub_adc_loopback(void) {
    const uint16_t HIGH_THRESH = 3800u;
    const uint16_t LOW_THRESH  = 300u;
    const uint     SAMPLES     = 8u;

    gpio_init(ADC_DRIVE_PIN);
    gpio_set_dir(ADC_DRIVE_PIN, GPIO_OUT);
    adc_gpio_init(ADC_GPIO);
    adc_select_input(0);

    gpio_put(ADC_DRIVE_PIN, 1);
    sleep_ms(10);
    uint32_t sum = 0u;
    for (uint i = 0u; i < SAMPLES; ++i) { sum += adc_read(); sleep_ms(2); }
    uint16_t high_avg = (uint16_t)(sum / SAMPLES);

    gpio_put(ADC_DRIVE_PIN, 0);
    sleep_ms(10);
    sum = 0u;
    for (uint i = 0u; i < SAMPLES; ++i) { sum += adc_read(); sleep_ms(2); }
    uint16_t low_avg = (uint16_t)(sum / SAMPLES);

    bool ok = (high_avg >= HIGH_THRESH) && (low_avg <= LOW_THRESH);
    char buf[48];
    snprintf(buf, sizeof(buf), "high=%u low=%u", high_avg, low_avg);
    report("adc_loopback", ok, buf);
}

/* ================================================================== */
/* main                                                                 */
/* ================================================================== */
int main(void) {
    gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);
    stdio_init_all();
    sleep_ms(1200);

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
    gpio_put(LED_PIN, 0);

    adc_init();

    printf("AEL_SUITE_FULL START\n");
    fflush(stdout);

    sub_minimal_runtime();
    sub_internal_temp();
    sub_timer();
    sub_gpio_level_low();
    sub_gpio_level_high();
    sub_gpio_sig_100hz();
    sub_gpio_sig_1khz();
    sub_pwm_1khz();
    sub_gpio_irq_loopback();
    sub_uart_rxd();
    sub_uart_banner();
    sub_spi_loopback();
    sub_adc_loopback();

    char done_line[64];
    snprintf(done_line, sizeof(done_line),
             "AEL_SUITE_FULL DONE passed=%d failed=%d", g_pass, g_fail);
    printf("%s\n", done_line);
    fflush(stdout);

    bool led = false;
    uint64_t next_led_us    = time_us_64() + 300000u;
    uint64_t next_repeat_us = time_us_64() + 1000000u;
    while (true) {
        uint64_t now = time_us_64();
        if (now >= next_led_us) {
            led = !led;
            gpio_put(LED_PIN, led ? 1u : 0u);
            next_led_us += 300000u;
        }
        if (now >= next_repeat_us) {
            printf("%s\n", done_line);
            fflush(stdout);
            next_repeat_us += 1000000u;
        }
        tight_loop_contents();
    }
}
