/*
 * test_pwm — Stage 1: LEDC PWM self-test (no external wiring)
 *
 * Configures LEDC at 1 kHz, 50% duty on GPIO32.
 * Pass criterion: both timer and channel config return ESP_OK.
 * Output: AEL_PWM gpio=GPIO32 freq_hz=1000 duty_pct=50 PASS|FAIL
 */

#include <stdio.h>
#include "ael_board_init.h"
#include "driver/ledc.h"

#define PWM_GPIO GPIO_NUM_32

void app_main(void)
{
    ael_common_init();

    ledc_timer_config_t tcfg = {
        .speed_mode      = LEDC_LOW_SPEED_MODE,
        .timer_num       = LEDC_TIMER_0,
        .duty_resolution = LEDC_TIMER_10_BIT,
        .freq_hz         = 1000,
        .clk_cfg         = LEDC_AUTO_CLK,
    };
    esp_err_t te = ledc_timer_config(&tcfg);

    ledc_channel_config_t ccfg = {
        .gpio_num   = PWM_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel    = LEDC_CHANNEL_0,
        .timer_sel  = LEDC_TIMER_0,
        .duty       = 512,   /* 50% of 1024 */
        .hpoint     = 0,
    };
    esp_err_t ce = ledc_channel_config(&ccfg);

    int ok = (te == ESP_OK && ce == ESP_OK);
    printf("AEL_PWM gpio=GPIO%d freq_hz=1000 duty_pct=50 %s\n", PWM_GPIO, ok ? "PASS" : "FAIL");
}
