/*
 * test_pcnt — Stage 2: PCNT pulse counter loopback
 *
 * Wiring required: GPIO25 ↔ GPIO26
 *   GPIO25 = output (drive)
 *   GPIO26 = PCNT input (edge count)
 *
 * Drives 100 pulses on GPIO25 and verifies PCNT counts exactly 100.
 * Output: AEL_PCNT sent=100 counted=N PASS|FAIL
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "ael_board_init.h"
#include "driver/gpio.h"
#include "driver/pulse_cnt.h"
#include "esp_rom_sys.h"

#define PCNT_DRIVE GPIO_NUM_25
#define PCNT_INPUT GPIO_NUM_26

void app_main(void)
{
    ael_common_init();

    gpio_config_t gc = {
        .pin_bit_mask  = 1ULL << PCNT_DRIVE,
        .mode          = GPIO_MODE_OUTPUT,
        .pull_up_en    = GPIO_PULLUP_DISABLE,
        .pull_down_en  = GPIO_PULLDOWN_DISABLE,
        .intr_type     = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc);
    gpio_set_level(PCNT_DRIVE, 0);

    pcnt_unit_config_t ucfg = { .low_limit = -1, .high_limit = 200 };
    pcnt_unit_handle_t unit = NULL;
    pcnt_new_unit(&ucfg, &unit);

    pcnt_chan_config_t ccfg = { .edge_gpio_num = PCNT_INPUT, .level_gpio_num = -1 };
    pcnt_channel_handle_t chan = NULL;
    pcnt_new_channel(unit, &ccfg, &chan);
    pcnt_channel_set_edge_action(chan,
        PCNT_CHANNEL_EDGE_ACTION_INCREASE, PCNT_CHANNEL_EDGE_ACTION_HOLD);
    pcnt_channel_set_level_action(chan,
        PCNT_CHANNEL_LEVEL_ACTION_KEEP, PCNT_CHANNEL_LEVEL_ACTION_KEEP);

    pcnt_unit_enable(unit);
    pcnt_unit_clear_count(unit);
    pcnt_unit_start(unit);

    for (int i = 0; i < 100; i++) {
        gpio_set_level(PCNT_DRIVE, 1); esp_rom_delay_us(10);
        gpio_set_level(PCNT_DRIVE, 0); esp_rom_delay_us(10);
    }
    vTaskDelay(pdMS_TO_TICKS(10));

    int count = 0;
    pcnt_unit_get_count(unit, &count);
    pcnt_unit_stop(unit);
    pcnt_unit_disable(unit);

    int ok = (count == 100);
    printf("AEL_PCNT sent=100 counted=%d %s\n", count, ok ? "PASS" : "FAIL");
}
