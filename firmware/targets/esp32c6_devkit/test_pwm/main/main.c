/* test_pwm — Stage 1: LEDC 1kHz 50% on GPIO3. No wiring required. */
#include <stdio.h>
#include "ael_board_init.h"
#include "driver/ledc.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define PWM_GPIO GPIO_NUM_3

void app_main(void)
{
    ael_common_init();
    ledc_timer_config_t tc = {
        .speed_mode      = LEDC_LOW_SPEED_MODE,
        .timer_num       = LEDC_TIMER_0,
        .duty_resolution = LEDC_TIMER_10_BIT,
        .freq_hz         = 1000,
        .clk_cfg         = LEDC_AUTO_CLK,
    };
    esp_err_t te = ledc_timer_config(&tc);
    ledc_channel_config_t cc = {
        .gpio_num   = PWM_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel    = LEDC_CHANNEL_0,
        .timer_sel  = LEDC_TIMER_0,
        .duty       = 512,
        .hpoint     = 0,
    };
    esp_err_t ce = ledc_channel_config(&cc);
    int ok = (te == ESP_OK && ce == ESP_OK);
    printf("AEL_PWM gpio=GPIO%d freq_hz=1000 duty_pct=50 %s\n",
           PWM_GPIO, ok ? "PASS" : "FAIL");
    ledc_stop(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
    while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
}
