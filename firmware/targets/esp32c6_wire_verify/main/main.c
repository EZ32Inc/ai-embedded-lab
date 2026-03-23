/*
 * esp32c6_wire_verify
 *
 * Drives GPIO2..7 at six distinct frequencies so the LA can identify
 * each wire by its frequency, regardless of the declared wiring.
 *
 * GPIO → Freq    → half-period µs
 *   2  → ~10 Hz  → 50 000
 *   3  → ~20 Hz  → 25 000
 *   4  → ~33 Hz  → 15 000
 *   5  → ~50 Hz  → 10 000
 *   6  → ~100 Hz →  5 000
 *   7  → ~200 Hz →  2 500
 *
 * LA capture (ael la-check --pin P0.x --duration-s 1):
 *   edges in 1 s ≈ freq × 2
 *   ~20  → GPIO2 (10 Hz)
 *   ~40  → GPIO3 (20 Hz)
 *   ~66  → GPIO4 (33 Hz)
 *   ~100 → GPIO5 (50 Hz)
 *   ~200 → GPIO6 (100 Hz)
 *   ~400 → GPIO7 (200 Hz)
 *
 * UART0: AEL_WIRE BOOT  then  AEL_WIRE RUNNING every 3 s
 */
#include <stdio.h>
#include <stdint.h>
#include "driver/gpio.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const gpio_num_t PINS[6] = {
    GPIO_NUM_2, GPIO_NUM_3, GPIO_NUM_4,
    GPIO_NUM_5, GPIO_NUM_6, GPIO_NUM_7,
};
static const int64_t HALF_US[6] = {
    50000, 25000, 15000, 10000, 5000, 2500,
};

void app_main(void)
{
    esp_task_wdt_deinit();
    vTaskDelay(pdMS_TO_TICKS(2000));
    printf("AEL_WIRE BOOT\n"); fflush(stdout);

    for (int i = 0; i < 6; i++) {
        gpio_config_t cfg = {
            .pin_bit_mask = 1ULL << PINS[i],
            .mode         = GPIO_MODE_OUTPUT,
            .pull_up_en   = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type    = GPIO_INTR_DISABLE,
        };
        gpio_config(&cfg);
        gpio_set_level(PINS[i], 0);
    }

    printf("AEL_WIRE gpio2=10Hz gpio3=20Hz gpio4=33Hz gpio5=50Hz gpio6=100Hz gpio7=200Hz\n");
    fflush(stdout);

    int64_t next[6];
    uint8_t state[6] = {0};
    int64_t now = esp_timer_get_time();
    /* stagger start times to avoid simultaneous edges */
    for (int i = 0; i < 6; i++) next[i] = now + HALF_US[i] * (i + 1);
    int64_t last_print = now;

    while (1) {
        now = esp_timer_get_time();
        for (int i = 0; i < 6; i++) {
            if (now >= next[i]) {
                next[i] += HALF_US[i];
                state[i] ^= 1;
                gpio_set_level(PINS[i], state[i]);
            }
        }
        if (now - last_print >= 3000000LL) {
            last_print = now;
            printf("AEL_WIRE RUNNING\n"); fflush(stdout);
        }
        taskYIELD();
    }
}
