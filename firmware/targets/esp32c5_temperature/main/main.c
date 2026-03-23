/*
 * esp32c5_temperature
 *
 * Reads the ESP32-C5 internal temperature sensor 5 times and prints each
 * reading. No wiring required.
 *
 * Patterns (on UART0 bridge, /dev/ttyACM0):
 *   AEL_TEMP <value> C   — one reading per sample
 *   AEL_TEMP DONE        — all samples complete
 */

#include <stdio.h>
#include "driver/temperature_sensor.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define SAMPLE_COUNT  5
#define SAMPLE_MS     500

void app_main(void)
{
    temperature_sensor_handle_t sensor = NULL;
    temperature_sensor_config_t cfg = TEMPERATURE_SENSOR_CONFIG_DEFAULT(10, 50);
    temperature_sensor_install(&cfg, &sensor);
    temperature_sensor_enable(sensor);

    for (int i = 0; i < SAMPLE_COUNT; i++) {
        float celsius = 0.0f;
        temperature_sensor_get_celsius(sensor, &celsius);
        printf("AEL_TEMP %.1f C\n", celsius);
        vTaskDelay(pdMS_TO_TICKS(SAMPLE_MS));
    }

    temperature_sensor_disable(sensor);
    temperature_sensor_uninstall(sensor);

    printf("AEL_TEMP DONE\n");
}
