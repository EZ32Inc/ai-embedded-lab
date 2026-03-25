/*
 * test_adc — Stage 2: ADC1 loopback via GPIO drive
 *
 * Wiring required: GPIO33 → GPIO34
 *   GPIO33 = digital output (drive high/low)
 *   GPIO34 = ADC1_CH6 input (input-only pin on ESP32 classic)
 *
 * Drives GPIO33 high then low and checks that ADC readings cross thresholds.
 * Output: AEL_ADC raw_hi=N raw_lo=N PASS|FAIL
 *
 * Note: ADC2 is unavailable while WiFi is active; this test uses ADC1 only.
 *       GPIO34–GPIO39 are input-only on ESP32 classic.
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "ael_board_init.h"
#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"

#define ADC_DRIVE      GPIO_NUM_33
#define ADC_UNIT       ADC_UNIT_1
#define ADC_CHAN       ADC_CHANNEL_6    /* GPIO34 = ADC1_CH6 on ESP32 */
#define ADC_ATTEN      ADC_ATTEN_DB_12
#define ADC_HI_THRESH  2000
#define ADC_LO_THRESH   500

void app_main(void)
{
    ael_common_init();

    gpio_config_t gc = {
        .pin_bit_mask  = 1ULL << ADC_DRIVE,
        .mode          = GPIO_MODE_OUTPUT,
        .pull_up_en    = GPIO_PULLUP_DISABLE,
        .pull_down_en  = GPIO_PULLDOWN_DISABLE,
        .intr_type     = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc);

    adc_oneshot_unit_handle_t adc;
    adc_oneshot_unit_init_cfg_t unit_cfg = { .unit_id = ADC_UNIT };
    adc_oneshot_new_unit(&unit_cfg, &adc);

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten    = ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    adc_oneshot_config_channel(adc, ADC_CHAN, &chan_cfg);

    gpio_set_level(ADC_DRIVE, 1); vTaskDelay(pdMS_TO_TICKS(20));
    int raw_hi = 0; adc_oneshot_read(adc, ADC_CHAN, &raw_hi);

    gpio_set_level(ADC_DRIVE, 0); vTaskDelay(pdMS_TO_TICKS(20));
    int raw_lo = 0; adc_oneshot_read(adc, ADC_CHAN, &raw_lo);

    adc_oneshot_del_unit(adc);

    int ok = (raw_hi > ADC_HI_THRESH) && (raw_lo < ADC_LO_THRESH);
    printf("AEL_ADC raw_hi=%d raw_lo=%d %s\n", raw_hi, raw_lo, ok ? "PASS" : "FAIL");
}
