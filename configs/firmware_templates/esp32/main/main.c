/* {SLUG} — AEL draft firmware template (Group: esp32)
 *
 * PLACEHOLDER: verify GPIO pin assignments for your board.
 *   AEL_GPIO_BASE: first signature output pin (e.g. GPIO4)
 *   AEL_LED_GPIO:  onboard LED pin (varies by board)
 */
#include <stdio.h>
#include <stdint.h>
#include "driver/gpio.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#ifndef AEL_GPIO_BASE
#define AEL_GPIO_BASE 4          /* PLACEHOLDER: first signature output GPIO */
#endif

#ifndef AEL_LED_GPIO
#define AEL_LED_GPIO  8          /* PLACEHOLDER: LED GPIO pin */
#endif

#ifndef AEL_BASE_FREQ_HZ
#define AEL_BASE_FREQ_HZ 50000
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

    const gpio_num_t pins[2] = {
        (gpio_num_t)(AEL_GPIO_BASE + 0),
        (gpio_num_t)(AEL_GPIO_BASE + 1),
    };
    for (int i = 0; i < 2; i++) {
        gpio_init_out(pins[i]);
        gpio_set_level(pins[i], 0);
    }
    gpio_init_out((gpio_num_t)AEL_LED_GPIO);
    gpio_set_level((gpio_num_t)AEL_LED_GPIO, 0);

    printf("AEL_READY {MCU_UPPER}\n");

    const int64_t period_us = 1000000LL / (2 * (int64_t)AEL_BASE_FREQ_HZ);
    int64_t now = esp_timer_get_time();
    int64_t next0 = now + period_us;
    int64_t next1 = now + period_us * 2;
    int64_t next_led = now + 500000;
    int64_t last_yield = now;
    uint8_t s0 = 0, s1 = 0, led = 0;

    while (1) {
        now = esp_timer_get_time();
        if (now >= next0) { next0 += period_us;     s0 ^= 1; gpio_set_level(pins[0], s0); }
        if (now >= next1) { next1 += period_us * 2; s1 ^= 1; gpio_set_level(pins[1], s1); }
        if (now >= next_led) {
            next_led += 500000;
            led ^= 1;
            gpio_set_level((gpio_num_t)AEL_LED_GPIO, led);
        }
        if (now - last_yield >= 5000) { last_yield = now; taskYIELD(); }
    }
}
