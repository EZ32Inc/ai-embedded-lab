/*
 * esp32c5_pin_toggle
 *
 * Toggles GPIO2, GPIO3, GPIO5, GPIO6 at different rates so the
 * logic analyser can identify each channel independently.
 *
 * Rates (approx):
 *   GPIO6  : 100 Hz  (5 ms HIGH, 5 ms LOW)   → P0.3
 *   GPIO5  :  50 Hz  (10 ms / 10 ms)          → P0.2
 *   GPIO3  :  25 Hz  (20 ms / 20 ms)          → P0.1
 *   GPIO2  :  12 Hz  (40 ms / 40 ms)          → P0.0
 *
 * Output on UART0: AEL_TOGGLE BOOT  then  AEL_TOGGLE RUNNING  every 2 s
 */

#include <stdio.h>
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static void setup_out(gpio_num_t pin)
{
    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << pin,
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
}

static void toggle_task_gpio6(void *arg)
{
    for (;;) {
        gpio_set_level(GPIO_NUM_6, 1); vTaskDelay(pdMS_TO_TICKS(5));
        gpio_set_level(GPIO_NUM_6, 0); vTaskDelay(pdMS_TO_TICKS(5));
    }
}

static void toggle_task_gpio5(void *arg)
{
    for (;;) {
        gpio_set_level(GPIO_NUM_5, 1); vTaskDelay(pdMS_TO_TICKS(10));
        gpio_set_level(GPIO_NUM_5, 0); vTaskDelay(pdMS_TO_TICKS(10));
    }
}

static void toggle_task_gpio3(void *arg)
{
    for (;;) {
        gpio_set_level(GPIO_NUM_3, 1); vTaskDelay(pdMS_TO_TICKS(20));
        gpio_set_level(GPIO_NUM_3, 0); vTaskDelay(pdMS_TO_TICKS(20));
    }
}

static void toggle_task_gpio2(void *arg)
{
    for (;;) {
        gpio_set_level(GPIO_NUM_2, 1); vTaskDelay(pdMS_TO_TICKS(40));
        gpio_set_level(GPIO_NUM_2, 0); vTaskDelay(pdMS_TO_TICKS(40));
    }
}

void app_main(void)
{
    vTaskDelay(pdMS_TO_TICKS(2000));
    printf("AEL_TOGGLE BOOT\n");
    fflush(stdout);

    setup_out(GPIO_NUM_2);
    setup_out(GPIO_NUM_3);
    setup_out(GPIO_NUM_5);
    setup_out(GPIO_NUM_6);

    xTaskCreate(toggle_task_gpio6, "tog6", 1024, NULL, 5, NULL);
    xTaskCreate(toggle_task_gpio5, "tog5", 1024, NULL, 5, NULL);
    xTaskCreate(toggle_task_gpio3, "tog3", 1024, NULL, 5, NULL);
    xTaskCreate(toggle_task_gpio2, "tog2", 1024, NULL, 5, NULL);

    for (;;) {
        printf("AEL_TOGGLE RUNNING\n");
        fflush(stdout);
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}
