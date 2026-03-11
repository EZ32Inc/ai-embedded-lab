#include <stdio.h>
#include <stdint.h>

#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
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

    adc_oneshot_unit_handle_t adc = NULL;
    adc_oneshot_unit_init_cfg_t unit_cfg = {
        .unit_id = ADC_UNIT_1,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    adc_oneshot_new_unit(&unit_cfg, &adc);
    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    adc_oneshot_config_channel(adc, ADC_CHANNEL_0, &chan_cfg);

    printf("AEL_READY ESP32C6 ADC\n");

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
            int sample = 0;
            adc_oneshot_read(adc, ADC_CHANNEL_0, &sample);
            next_banner += 1000000;
            printf("AEL_READY ESP32C6 ADC sample=%d\n", sample);
        }
        if (now - last_yield >= 5000) {
            last_yield = now;
            taskYIELD();
        }
    }
}
