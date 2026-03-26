/* hello — Stage 0: bare-board smoke test for ESP32-C3 DevKit (native USB). */
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void app_main(void)
{
    /* Native USB CDC: print in a loop so observer catches it regardless of timing */
    while (1) {
        printf("AEL_HELLO board=ESP32C3 PASS\n");
        fflush(stdout);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
