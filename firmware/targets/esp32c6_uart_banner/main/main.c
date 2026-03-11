#include <stdio.h>
#include <stdint.h>

#include "driver/gpio.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static void gpio_init_out(gpio_num_t pin) {
    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << pin,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
}

void app_main(void) {
    esp_task_wdt_deinit();

    const gpio_num_t pins[4] = {
        GPIO_NUM_4,
        GPIO_NUM_5,
        GPIO_NUM_6,
        GPIO_NUM_7,
    };

    for (int i = 0; i < 4; i++) {
        gpio_init_out(pins[i]);
        gpio_set_level(pins[i], 0);
    }
    gpio_set_level(pins[2], 1);
    gpio_set_level(pins[3], 0);

    printf("AEL_READY ESP32C6 UART\n");

    int64_t now = esp_timer_get_time();
    int64_t next0 = now + 1000;
    int64_t next1 = now + 500;
    int64_t next_banner = now + 1000000;
    int64_t last_yield = now;
    uint8_t state0 = 0;
    uint8_t state1 = 0;

    while (1) {
        now = esp_timer_get_time();
        if (now >= next0) {
            next0 += 1000;
            state0 ^= 1;
            gpio_set_level(pins[0], state0);
        }
        if (now >= next1) {
            next1 += 500;
            state1 ^= 1;
            gpio_set_level(pins[1], state1);
        }
        if (now >= next_banner) {
            next_banner += 1000000;
            printf("AEL_READY ESP32C6 UART\n");
        }
        if (now - last_yield >= 5000) {
            last_yield = now;
            taskYIELD();
        }
    }
}
