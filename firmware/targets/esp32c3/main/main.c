#include <stdio.h>
#include <stdint.h>

#include "driver/gpio.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#ifndef AEL_GPIO_BASE
#define AEL_GPIO_BASE 4
#endif

#ifndef AEL_LED_GPIO
#define AEL_LED_GPIO 8
#endif

#ifndef AEL_BASE_FREQ_HZ
#define AEL_BASE_FREQ_HZ 50000
#endif

#ifndef AEL_LED_BLINK_HZ
#define AEL_LED_BLINK_HZ 1
#endif

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
        (gpio_num_t)(AEL_GPIO_BASE + 0),
        (gpio_num_t)(AEL_GPIO_BASE + 1),
        (gpio_num_t)(AEL_GPIO_BASE + 2),
        (gpio_num_t)(AEL_GPIO_BASE + 3),
    };

    for (int i = 0; i < 4; i++) {
        gpio_init_out(pins[i]);
        gpio_set_level(pins[i], 0);
    }

    gpio_init_out((gpio_num_t)AEL_LED_GPIO);
    gpio_set_level((gpio_num_t)AEL_LED_GPIO, 0);

    printf("AEL_READY ESP32C3\n");

    const int64_t base_period_us = 1000000LL / (2 * (int64_t)AEL_BASE_FREQ_HZ);
    const int64_t led_period_us = 1000000LL / (2 * (int64_t)AEL_LED_BLINK_HZ);

    int64_t now = esp_timer_get_time();
    int64_t next0 = now + base_period_us;
    int64_t next1 = now + base_period_us * 2;
    int64_t next2 = now + base_period_us * 3;
    int64_t next3 = now + base_period_us * 4;
    int64_t next_led = now + led_period_us;
    int64_t last_yield = now;

    uint8_t state0 = 0;
    uint8_t state1 = 0;
    uint8_t state2 = 0;
    uint8_t state3 = 0;
    uint8_t led_state = 0;

    while (1) {
        now = esp_timer_get_time();

        if (now >= next0) {
            next0 += base_period_us;
            state0 ^= 1;
            gpio_set_level(pins[0], state0);
        }
        if (now >= next1) {
            next1 += base_period_us * 2;
            state1 ^= 1;
            gpio_set_level(pins[1], state1);
        }
        if (now >= next2) {
            next2 += base_period_us * 3;
            state2 ^= 1;
            gpio_set_level(pins[2], state2);
        }
        if (now >= next3) {
            next3 += base_period_us * 4;
            state3 ^= 1;
            gpio_set_level(pins[3], state3);
        }

        if (now >= next_led) {
            next_led += led_period_us;
            led_state ^= 1;
            gpio_set_level((gpio_num_t)AEL_LED_GPIO, led_state);
        }

        if (now - last_yield >= 5000) {
            last_yield = now;
            taskYIELD();
        }
    }
}
