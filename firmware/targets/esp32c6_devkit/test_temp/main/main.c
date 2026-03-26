/* test_temp — Stage 1: internal temperature sensor. No wiring required. */
#include <stdio.h>
#include "ael_board_init.h"
#include "driver/temperature_sensor.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void app_main(void)
{
    ael_common_init();
    temperature_sensor_handle_t sensor = NULL;
    temperature_sensor_config_t cfg = TEMPERATURE_SENSOR_CONFIG_DEFAULT(10, 80);
    esp_err_t e = temperature_sensor_install(&cfg, &sensor);
    if (e != ESP_OK) { printf("AEL_TEMP install_err=0x%x FAIL\n", e); return; }
    temperature_sensor_enable(sensor);
    float celsius = 0.0f;
    temperature_sensor_get_celsius(sensor, &celsius);
    temperature_sensor_disable(sensor);
    temperature_sensor_uninstall(sensor);
    int ok = (celsius > 5.0f && celsius < 90.0f);
    printf("AEL_TEMP celsius=%.1f %s\n", celsius, ok ? "PASS" : "FAIL");
    while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
}
