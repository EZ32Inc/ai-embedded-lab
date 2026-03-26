/* hello — Stage 0 bare-board smoke test for ESP32-S3 DevKit.
 * No wiring required. Prints AEL_HELLO PASS and halts. */
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void app_main(void)
{
    printf("AEL_HELLO board=ESP32S3 PASS\n");
    fflush(stdout);
    while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
}
