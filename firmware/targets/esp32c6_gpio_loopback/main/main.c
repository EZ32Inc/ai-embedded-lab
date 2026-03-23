/*
 * esp32c6_gpio_loopback
 *
 * Tests three adjacent GPIO pairs as digital loopback.
 * Adjacent pairs are easy to jumper on the DevKit header.
 *
 *   Pair A: GPIO18 (out) --> jumper --> GPIO19 (in)
 *   Pair B: GPIO20 (out) --> jumper --> GPIO21 (in)
 *   Pair C: GPIO22 (out) --> jumper --> GPIO23 (in)
 *
 * LA wires (P0.0-P0.3 on GPIO2/3/5/6) remain in place and are used
 * in the post-test toggle phase to confirm LA connectivity.
 *
 * UART0 output (115200 8N1):
 *   AEL_LOOPBACK BOOT
 *   AEL_LOOPBACK pair=A out=GPIO18 in=GPIO19 hi_rd=<0|1> lo_rd=<0|1> <PASS|FAIL>
 *   AEL_LOOPBACK pair=B out=GPIO20 in=GPIO21 hi_rd=<0|1> lo_rd=<0|1> <PASS|FAIL>
 *   AEL_LOOPBACK pair=C out=GPIO22 in=GPIO23 hi_rd=<0|1> lo_rd=<0|1> <PASS|FAIL>
 *   AEL_LOOPBACK DONE passed=<n> failed=<n>
 *
 * Post-test: GPIO3/5/6 toggle for LA observation (P0.1/P0.2/P0.3).
 *   GPIO3 ~50 Hz, GPIO5 ~100 Hz, GPIO6 ~200 Hz
 *   (actual ~halved by taskYIELD overhead)
 */
#include <stdio.h>
#include "driver/gpio.h"
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
        .pull_down_en = GPIO_PULLDOWN_ENABLE,   /* default LOW when wire absent */
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
}

static void test_pair(gpio_num_t out_pin, gpio_num_t in_pin, char pair_id,
                      int *passed, int *failed)
{
    gpio_as_out(out_pin);
    gpio_as_in(in_pin);

    gpio_set_level(out_pin, 1);
    vTaskDelay(pdMS_TO_TICKS(20));
    int hi_rd = gpio_get_level(in_pin);

    gpio_set_level(out_pin, 0);
    vTaskDelay(pdMS_TO_TICKS(20));
    int lo_rd = gpio_get_level(in_pin);

    int ok = (hi_rd == 1) && (lo_rd == 0);
    if (ok) (*passed)++; else (*failed)++;

    printf("AEL_LOOPBACK pair=%c out=GPIO%d in=GPIO%d hi_rd=%d lo_rd=%d %s\n",
           pair_id, (int)out_pin, (int)in_pin, hi_rd, lo_rd, ok ? "PASS" : "FAIL");
    fflush(stdout);
}

void app_main(void)
{
    esp_task_wdt_deinit();
    vTaskDelay(pdMS_TO_TICKS(2000));
    printf("AEL_LOOPBACK BOOT\n");
    fflush(stdout);

    int passed = 0, failed = 0;
    test_pair(GPIO_NUM_18, GPIO_NUM_19, 'A', &passed, &failed);
    test_pair(GPIO_NUM_20, GPIO_NUM_21, 'B', &passed, &failed);
    test_pair(GPIO_NUM_22, GPIO_NUM_23, 'C', &passed, &failed);

    printf("AEL_LOOPBACK DONE passed=%d failed=%d\n", passed, failed);
    fflush(stdout);

    /* Configure GPIO3/5/6 as outputs for LA observation */
    gpio_as_out(GPIO_NUM_3);
    gpio_as_out(GPIO_NUM_5);
    gpio_as_out(GPIO_NUM_6);

    /* Continuous toggle: GPIO3 ~50 Hz, GPIO5 ~100 Hz, GPIO6 ~200 Hz */
    int64_t now        = esp_timer_get_time();
    int64_t next3      = now + 10000;   /* 10 ms half-period */
    int64_t next5      = now + 5000;    /*  5 ms half-period */
    int64_t next6      = now + 2500;    /*  2.5 ms half-period */
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
            printf("AEL_LOOPBACK RUNNING\n"); fflush(stdout);
        }
        if (now - last_yield >= 5000) { last_yield = now; taskYIELD(); }
    }
}
