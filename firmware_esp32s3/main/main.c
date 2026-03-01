#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"

#ifndef AEL_GPIO_BASE
#define AEL_GPIO_BASE 4
#endif

#ifndef AEL_LED_GPIO
#define AEL_LED_GPIO 48
#endif

#ifndef AEL_TOGGLE_DIV
#define AEL_TOGGLE_DIV 50
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
    const gpio_num_t pins[4] = {
        (gpio_num_t)(AEL_GPIO_BASE + 0),
        (gpio_num_t)(AEL_GPIO_BASE + 1),
        (gpio_num_t)(AEL_GPIO_BASE + 2),
        (gpio_num_t)(AEL_GPIO_BASE + 3),
    };

    for (int i = 0; i < 4; i++) {
        gpio_init_out(pins[i]);
    }
    gpio_init_out((gpio_num_t)AEL_LED_GPIO);

    printf("AEL_READY ESP32S3\n");

    uint32_t div0 = 0, div1 = 0, div2 = 0, div3 = 0;
    uint32_t led_div = 0;

    while (1) {
        if (++div0 >= AEL_TOGGLE_DIV) {
            div0 = 0;
            gpio_set_level(pins[0], !gpio_get_level(pins[0]));
        }
        if (++div1 >= AEL_TOGGLE_DIV * 2) {
            div1 = 0;
            gpio_set_level(pins[1], !gpio_get_level(pins[1]));
        }
        if (++div2 >= AEL_TOGGLE_DIV * 3) {
            div2 = 0;
            gpio_set_level(pins[2], !gpio_get_level(pins[2]));
        }
        if (++div3 >= AEL_TOGGLE_DIV * 4) {
            div3 = 0;
            gpio_set_level(pins[3], !gpio_get_level(pins[3]));
        }

        if (++led_div >= AEL_TOGGLE_DIV * 400) {
            led_div = 0;
            gpio_set_level((gpio_num_t)AEL_LED_GPIO, !gpio_get_level((gpio_num_t)AEL_LED_GPIO));
        }
    }
}
