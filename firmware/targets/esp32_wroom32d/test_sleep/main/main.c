/*
 * test_sleep — Stage 1: light sleep timer wakeup (no external wiring)
 *
 * Enters light sleep for 1 second via timer wakeup and checks cause.
 * Output: AEL_SLEEP wakeup_cause=N PASS|FAIL
 */

#include <stdio.h>
#include "ael_board_init.h"
#include "esp_sleep.h"

void app_main(void)
{
    ael_common_init();

    printf("AEL_SLEEP entering\n"); fflush(stdout);
    esp_sleep_enable_timer_wakeup(1000000ULL);   /* 1 second */
    esp_light_sleep_start();

    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    int ok = (cause == ESP_SLEEP_WAKEUP_TIMER);
    printf("AEL_SLEEP wakeup_cause=%d %s\n", (int)cause, ok ? "PASS" : "FAIL");
}
