/*
 * test_gpio_intr — Stage 2: GPIO interrupt loopback
 *
 * Wiring required: GPIO25 ↔ GPIO26
 *   GPIO25 = output (drive)
 *   GPIO26 = input  (interrupt on rising edge)
 *
 * Pulses GPIO25 20 times and counts interrupts on GPIO26.
 * Output: AEL_INTR triggered=N expected=20 PASS|FAIL
 *
 * Note: run this test BEFORE test_pcnt — both share GPIO25/26.
 *       PCNT occupies the pin after init and blocks GPIO interrupts.
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "ael_board_init.h"
#include "driver/gpio.h"
#include "esp_rom_sys.h"

#define INTR_DRIVE GPIO_NUM_25
#define INTR_INPUT GPIO_NUM_26

static volatile int s_intr_count = 0;

static void IRAM_ATTR gpio_isr_handler(void *arg)
{
    (void)arg;
    s_intr_count++;
}

void app_main(void)
{
    ael_common_init();
    ael_gpio_isr_init();

    gpio_config_t gc_out = {
        .pin_bit_mask  = 1ULL << INTR_DRIVE,
        .mode          = GPIO_MODE_OUTPUT,
        .pull_up_en    = GPIO_PULLUP_DISABLE,
        .pull_down_en  = GPIO_PULLDOWN_DISABLE,
        .intr_type     = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc_out);
    gpio_set_level(INTR_DRIVE, 0);

    gpio_config_t gc_in = {
        .pin_bit_mask  = 1ULL << INTR_INPUT,
        .mode          = GPIO_MODE_INPUT,
        .pull_up_en    = GPIO_PULLUP_DISABLE,
        .pull_down_en  = GPIO_PULLDOWN_ENABLE,
        .intr_type     = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc_in);

    s_intr_count = 0;
    gpio_isr_handler_add(INTR_INPUT, gpio_isr_handler, NULL);
    gpio_set_intr_type(INTR_INPUT, GPIO_INTR_POSEDGE);
    gpio_intr_enable(INTR_INPUT);

    const int N = 20;
    for (int i = 0; i < N; i++) {
        gpio_set_level(INTR_DRIVE, 1); esp_rom_delay_us(200);
        gpio_set_level(INTR_DRIVE, 0); esp_rom_delay_us(200);
    }
    vTaskDelay(pdMS_TO_TICKS(20));

    gpio_intr_disable(INTR_INPUT);
    gpio_isr_handler_remove(INTR_INPUT);

    int ok = (s_intr_count == N);
    printf("AEL_INTR triggered=%d expected=%d %s\n", s_intr_count, N, ok ? "PASS" : "FAIL");
}
