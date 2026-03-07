#include <inttypes.h>
#include <stdio.h>

#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#ifndef AEL_GPIO_X1
#define AEL_GPIO_X1 4
#endif

#ifndef AEL_GPIO_X2
#define AEL_GPIO_X2 5
#endif

#ifndef AEL_GPIO_X3
#define AEL_GPIO_X3 6
#endif

#ifndef AEL_GPIO_X4
#define AEL_GPIO_X4 7
#endif

#ifndef AEL_GPIO_X1_FREQ_HZ
#define AEL_GPIO_X1_FREQ_HZ 1000
#endif

#ifndef AEL_GPIO_X2_FREQ_HZ
#define AEL_GPIO_X2_FREQ_HZ 2000
#endif

static uint8_t s_x1_level = 0;
static uint8_t s_x2_level = 0;
static const char *TAG = "ESP32C3 DUT";

static void gpio_out_init(gpio_num_t gpio, int initial_level) {
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << gpio),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
    gpio_set_level(gpio, initial_level);
}

static void x1_toggle_cb(void *arg) {
    (void)arg;
    s_x1_level ^= 1;
    gpio_set_level((gpio_num_t)AEL_GPIO_X1, s_x1_level);
}

static void x2_toggle_cb(void *arg) {
    (void)arg;
    s_x2_level ^= 1;
    gpio_set_level((gpio_num_t)AEL_GPIO_X2, s_x2_level);
}

void app_main(void) {
    gpio_out_init((gpio_num_t)AEL_GPIO_X1, 0);
    gpio_out_init((gpio_num_t)AEL_GPIO_X2, 0);
    gpio_out_init((gpio_num_t)AEL_GPIO_X3, 1);
    gpio_out_init((gpio_num_t)AEL_GPIO_X4, 0);

    const esp_timer_create_args_t x1_timer_args = {
        .callback = &x1_toggle_cb,
        .arg = NULL,
        .dispatch_method = ESP_TIMER_TASK,
        .name = "x1_1khz",
        .skip_unhandled_events = true,
    };
    const esp_timer_create_args_t x2_timer_args = {
        .callback = &x2_toggle_cb,
        .arg = NULL,
        .dispatch_method = ESP_TIMER_TASK,
        .name = "x2_2khz",
        .skip_unhandled_events = true,
    };

    esp_timer_handle_t x1_timer = NULL;
    esp_timer_handle_t x2_timer = NULL;
    esp_timer_create(&x1_timer_args, &x1_timer);
    esp_timer_create(&x2_timer_args, &x2_timer);

    const int64_t x1_period_us = (1000000LL / (2LL * (int64_t)AEL_GPIO_X1_FREQ_HZ));
    const int64_t x2_period_us = (1000000LL / (2LL * (int64_t)AEL_GPIO_X2_FREQ_HZ));
    esp_timer_start_periodic(x1_timer, x1_period_us);
    esp_timer_start_periodic(x2_timer, x2_period_us);

    printf("AEL_DUT_READY\n");
    ESP_LOGI(TAG, "Hello world from ESP32C3 DUT by AEL");
    printf(
        "AEL_GPIO_SIGNATURE X1=%d@%dHz X2=%d@%dHz X3=%d(high) X4=%d(low)\n",
        AEL_GPIO_X1,
        AEL_GPIO_X1_FREQ_HZ,
        AEL_GPIO_X2,
        AEL_GPIO_X2_FREQ_HZ,
        AEL_GPIO_X3,
        AEL_GPIO_X4);

    while (1) {
        printf("AEL_DUT_READY\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
