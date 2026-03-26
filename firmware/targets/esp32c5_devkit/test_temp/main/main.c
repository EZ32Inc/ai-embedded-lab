#include <stdio.h>
#include "esp_log.h"
#include "driver/temperature_sensor.h"
#include "driver/gpio.h"
#include "nvs_flash.h"

void app_main(void)
{
    esp_log_level_set("*", ESP_LOG_WARN);
    gpio_install_isr_service(0);
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase(); nvs_flash_init();
    }

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
    fflush(stdout);
}
