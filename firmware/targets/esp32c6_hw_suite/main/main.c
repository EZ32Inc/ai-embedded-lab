/*
 * esp32c6_hw_suite
 *
 * Three-experiment hardware verification suite for ESP32-C6.
 *
 * Connections required:
 *   GPIO20 <--> GPIO21   (jumper)  — GPIO digital loopback
 *   GPIO18 <--> GPIO19   (jumper)  — UART1 TX/RX loopback
 *   GPIO22 <--> GPIO4    (jumper)  — ADC loopback (GPIO22 drives, GPIO4 = ADC1_CH4)
 *
 * LA wires (P0.0-P0.3) remain on GPIO2/3/5/6 for post-test observation.
 *
 * UART0 output (115200 8N1):
 *   AEL_SUITE BOOT
 *   AEL_GPIO  drv=GPIO20 rdb=GPIO21 hi_rd=<0|1> lo_rd=<0|1> <PASS|FAIL>
 *   AEL_UART  port=UART1 tx=GPIO18 rx=GPIO19 sent=<n> recv=<n> match=<0|1> <PASS|FAIL>
 *   AEL_ADC   drv=GPIO22 adc=GPIO4(CH4) raw_hi=<n> raw_lo=<n> <PASS|FAIL>
 *   AEL_SUITE DONE passed=<n> failed=<n>
 *
 * Post-test: GPIO3/5/6 toggle for LA observation (~50/100/200 Hz, halved by yield).
 */
#include <stdio.h>
#include <string.h>
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static void gpio_as_out(gpio_num_t pin)
{
    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << pin,
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
}

static void gpio_as_in(gpio_num_t pin)
{
    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << pin,
        .mode         = GPIO_MODE_INPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
}

/* ---- Experiment 1: GPIO digital loopback ---- */

static int test_gpio(int *passed, int *failed)
{
    gpio_as_out(GPIO_NUM_20);
    gpio_as_in(GPIO_NUM_21);

    gpio_set_level(GPIO_NUM_20, 1);
    vTaskDelay(pdMS_TO_TICKS(20));
    int hi_rd = gpio_get_level(GPIO_NUM_21);

    gpio_set_level(GPIO_NUM_20, 0);
    vTaskDelay(pdMS_TO_TICKS(20));
    int lo_rd = gpio_get_level(GPIO_NUM_21);

    int ok = (hi_rd == 1) && (lo_rd == 0);
    if (ok) (*passed)++; else (*failed)++;
    printf("AEL_GPIO drv=GPIO20 rdb=GPIO21 hi_rd=%d lo_rd=%d %s\n",
           hi_rd, lo_rd, ok ? "PASS" : "FAIL");
    fflush(stdout);
    return ok;
}

/* ---- Experiment 2: UART loopback ---- */

#define UART1_PORT UART_NUM_1
#define UART1_BAUD 115200
#define UART1_BUFSZ 256

static const char UART_TEST_MSG[] = "AEL_UART_PING";
#define UART_TEST_LEN ((int)(sizeof(UART_TEST_MSG) - 1))

static int test_uart(int *passed, int *failed)
{
    uart_config_t cfg = {
        .baud_rate  = UART1_BAUD,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .flow_ctrl  = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    uart_driver_install(UART1_PORT, UART1_BUFSZ, 0, 0, NULL, 0);
    uart_param_config(UART1_PORT, &cfg);
    uart_set_pin(UART1_PORT, GPIO_NUM_18, GPIO_NUM_19,
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    uart_flush(UART1_PORT);
    int sent = uart_write_bytes(UART1_PORT, UART_TEST_MSG, UART_TEST_LEN);

    uint8_t buf[32] = {0};
    int recv = uart_read_bytes(UART1_PORT, buf, UART_TEST_LEN,
                               pdMS_TO_TICKS(200));

    int match = (recv == UART_TEST_LEN) &&
                (memcmp(buf, UART_TEST_MSG, UART_TEST_LEN) == 0);
    int ok = (sent == UART_TEST_LEN) && match;

    if (ok) (*passed)++; else (*failed)++;
    printf("AEL_UART port=UART1 tx=GPIO18 rx=GPIO19 sent=%d recv=%d match=%d %s\n",
           sent, recv, match, ok ? "PASS" : "FAIL");
    fflush(stdout);

    uart_driver_delete(UART1_PORT);
    return ok;
}

/* ---- Experiment 3: ADC loopback ---- */

/* GPIO4 = ADC1_CH4 on ESP32-C6 */
#define ADC_DRIVE_PIN  GPIO_NUM_22
#define ADC_UNIT_ID    ADC_UNIT_1
#define ADC_CHAN       ADC_CHANNEL_4
#define ADC_ATTEN      ADC_ATTEN_DB_12
#define ADC_HI_THRESH  2000
#define ADC_LO_THRESH  500

static int test_adc(int *passed, int *failed)
{
    gpio_as_out(ADC_DRIVE_PIN);

    adc_oneshot_unit_handle_t adc;
    adc_oneshot_unit_init_cfg_t unit_cfg = {
        .unit_id  = ADC_UNIT_ID,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    adc_oneshot_new_unit(&unit_cfg, &adc);

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten    = ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    adc_oneshot_config_channel(adc, ADC_CHAN, &chan_cfg);

    gpio_set_level(ADC_DRIVE_PIN, 1);
    vTaskDelay(pdMS_TO_TICKS(20));
    int raw_hi = 0;
    adc_oneshot_read(adc, ADC_CHAN, &raw_hi);

    gpio_set_level(ADC_DRIVE_PIN, 0);
    vTaskDelay(pdMS_TO_TICKS(20));
    int raw_lo = 0;
    adc_oneshot_read(adc, ADC_CHAN, &raw_lo);

    adc_oneshot_del_unit(adc);

    int ok = (raw_hi > ADC_HI_THRESH) && (raw_lo < ADC_LO_THRESH);
    if (ok) (*passed)++; else (*failed)++;
    printf("AEL_ADC drv=GPIO22 adc=GPIO4(CH4) raw_hi=%d raw_lo=%d %s\n",
           raw_hi, raw_lo, ok ? "PASS" : "FAIL");
    fflush(stdout);
    return ok;
}

/* ---- app_main ---- */

void app_main(void)
{
    esp_task_wdt_deinit();
    vTaskDelay(pdMS_TO_TICKS(2000));
    printf("AEL_SUITE BOOT\n"); fflush(stdout);

    int passed = 0, failed = 0;
    test_gpio(&passed, &failed);
    test_uart(&passed, &failed);
    test_adc(&passed, &failed);

    printf("AEL_SUITE DONE passed=%d failed=%d\n", passed, failed);
    fflush(stdout);

    /* Post-test: toggle GPIO3/5/6 for LA observation */
    gpio_as_out(GPIO_NUM_3);
    gpio_as_out(GPIO_NUM_5);
    gpio_as_out(GPIO_NUM_6);

    int64_t now        = esp_timer_get_time();
    int64_t next3      = now + 10000;
    int64_t next5      = now +  5000;
    int64_t next6      = now +  2500;
    int64_t last_print = now;
    int64_t last_yield = now;
    uint8_t s3 = 0, s5 = 0, s6 = 0;

    while (1) {
        now = esp_timer_get_time();
        if (now >= next3) { next3 += 10000; s3 ^= 1; gpio_set_level(GPIO_NUM_3, s3); }
        if (now >= next5) { next5 +=  5000; s5 ^= 1; gpio_set_level(GPIO_NUM_5, s5); }
        if (now >= next6) { next6 +=  2500; s6 ^= 1; gpio_set_level(GPIO_NUM_6, s6); }
        if (now - last_print >= 3000000LL) {
            last_print = now;
            printf("AEL_SUITE RUNNING\n"); fflush(stdout);
        }
        if (now - last_yield >= 5000) { last_yield = now; taskYIELD(); }
    }
}
