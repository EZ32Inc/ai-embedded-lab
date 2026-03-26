#include <stdio.h>
#include "esp_log.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "esp_timer.h"

#define INTR_DRIVE GPIO_NUM_2
#define INTR_INPUT GPIO_NUM_3

static volatile int s_intr_count = 0;  /* DRAM — IRAM is execute-only on C5 with PMP split */

static void IRAM_ATTR gpio_isr_handler(void *arg)
{
    (void)arg;
    s_intr_count++;
}

static void busy_delay_us(uint32_t us)
{
    int64_t end = esp_timer_get_time() + (int64_t)us;
    while (esp_timer_get_time() < end) {}
}

void app_main(void)
{
    esp_log_level_set("*", ESP_LOG_WARN);
    gpio_install_isr_service(0);
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase(); nvs_flash_init();
    }

    gpio_config_t gc_out = {
        .pin_bit_mask = 1ULL << INTR_DRIVE, .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE, .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc_out);
    gpio_set_level(INTR_DRIVE, 0);

    gpio_config_t gc_in = {
        .pin_bit_mask = 1ULL << INTR_INPUT, .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE, .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc_in);

    s_intr_count = 0;
    gpio_isr_handler_add(INTR_INPUT, gpio_isr_handler, NULL);
    gpio_set_intr_type(INTR_INPUT, GPIO_INTR_POSEDGE);
    gpio_intr_enable(INTR_INPUT);

    const int N = 20;
    for (int i = 0; i < N; i++) {
        gpio_set_level(INTR_DRIVE, 1); busy_delay_us(200);
        gpio_set_level(INTR_DRIVE, 0); busy_delay_us(200);
    }
    vTaskDelay(pdMS_TO_TICKS(20));

    gpio_intr_disable(INTR_INPUT);
    gpio_isr_handler_remove(INTR_INPUT);

    int ok = (s_intr_count == N);
    printf("AEL_INTR triggered=%d expected=%d %s\n", s_intr_count, N, ok ? "PASS" : "FAIL");
    fflush(stdout);
}
