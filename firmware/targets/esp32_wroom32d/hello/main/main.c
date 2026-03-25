/*
 * hello — Stage 0 bare-board console validation for ESP32-WROOM-32D (CP210X)
 *
 * No jumpers. No peripherals. Only power + CP210X USB.
 * Prints 15 tick lines then AEL_HELLO_DONE.
 *
 * Must PASS before any wired test is attempted.
 * Flash: idf.py -p /dev/ttyUSB0 build flash monitor
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void app_main(void)
{
    printf("AEL_HELLO BOOT\n"); fflush(stdout);

    for (int i = 1; i <= 15; i++) {
        printf("AEL_HELLO tick=%d\n", i); fflush(stdout);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }

    printf("AEL_HELLO_DONE\n"); fflush(stdout);

    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}
