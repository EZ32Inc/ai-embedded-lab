/*
 * esp32_wroom32d_hello — minimal UART console health check
 *
 * Prints a counter line every second to UART0 (GPIO1 TX → CP210X → /dev/ttyUSB0).
 * No jumpers required. No peripherals touched.
 * Stops after 15 lines, prints AEL_HELLO_DONE, then idles.
 *
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
