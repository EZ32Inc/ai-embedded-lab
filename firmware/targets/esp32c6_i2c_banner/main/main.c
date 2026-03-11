#include <stdio.h>
#include <stdint.h>

#include "driver/gpio.h"
#include "driver/i2c.h"
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

    i2c_config_t cfg = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = GPIO_NUM_8,
        .scl_io_num = GPIO_NUM_9,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = 100000,
    };
    i2c_param_config(I2C_NUM_0, &cfg);
    i2c_driver_install(I2C_NUM_0, I2C_MODE_MASTER, 0, 0, 0);

    printf("AEL_READY ESP32C6 I2C\n");

    int64_t now = esp_timer_get_time();
    int64_t next0 = now + 1000;
    int64_t next1 = now + 500;
    int64_t next_banner = now + 1000000;
    int64_t last_yield = now;
    uint8_t state0 = 0;
    uint8_t state1 = 0;
    uint8_t tx = 0x33;

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
            i2c_cmd_handle_t cmd = i2c_cmd_link_create();
            i2c_master_start(cmd);
            i2c_master_write_byte(cmd, (0x42 << 1) | I2C_MASTER_WRITE, true);
            i2c_master_write_byte(cmd, tx, true);
            i2c_master_stop(cmd);
            i2c_master_cmd_begin(I2C_NUM_0, cmd, pdMS_TO_TICKS(2));
            i2c_cmd_link_delete(cmd);
            next_banner += 1000000;
            printf("AEL_READY ESP32C6 I2C tx=0x%02X\n", tx);
            tx++;
        }
        if (now - last_yield >= 5000) {
            last_yield = now;
            taskYIELD();
        }
    }
}
