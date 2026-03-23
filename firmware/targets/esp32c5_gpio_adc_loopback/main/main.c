/*
 * esp32c5_gpio_adc_loopback
 *
 * GPIO3 (output) drives GPIO2 (ADC1_CH1 input).
 * Measures high and low rail via ADC and verifies thresholds.
 * Requires Wire B: GPIO3 → GPIO2 jumper.
 *
 * Patterns (on UART0 bridge, /dev/ttyACM0):
 *   AEL_GPIOADC raw_hi=<n> raw_lo=<n> PASS
 *   AEL_GPIOADC raw_hi=<n> raw_lo=<n> FAIL
 */

#include <stdio.h>
#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define DRIVE_PIN    GPIO_NUM_6
#define ADC_UNIT     ADC_UNIT_1
#define ADC_CHAN     ADC_CHANNEL_0    /* GPIO1 = ADC1_CH0 on ESP32-C5 */
#define ADC_ATTEN    ADC_ATTEN_DB_12

/* 12-bit ADC (0-4095). 3.3 V full scale.
 * High: >2000 (> ~1.6 V)  Low: <500 (< ~0.4 V) */
#define HIGH_THRESH  2000
#define LOW_THRESH   500

void app_main(void)
{
    /* Wait for UART observer to connect */
    vTaskDelay(pdMS_TO_TICKS(2000));

    /* GPIO6 as output */
    gpio_config_t gcfg = {
        .pin_bit_mask = 1ULL << DRIVE_PIN,
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&gcfg);

    /* ADC oneshot on ADC1 */
    adc_oneshot_unit_handle_t adc;
    adc_oneshot_unit_init_cfg_t unit_cfg = { .unit_id = ADC_UNIT };
    adc_oneshot_new_unit(&unit_cfg, &adc);

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten    = ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    adc_oneshot_config_channel(adc, ADC_CHAN, &chan_cfg);

    /* Drive high, measure */
    gpio_set_level(DRIVE_PIN, 1);
    vTaskDelay(pdMS_TO_TICKS(20));
    int raw_hi = 0;
    adc_oneshot_read(adc, ADC_CHAN, &raw_hi);

    /* Drive low, measure */
    gpio_set_level(DRIVE_PIN, 0);
    vTaskDelay(pdMS_TO_TICKS(20));
    int raw_lo = 0;
    adc_oneshot_read(adc, ADC_CHAN, &raw_lo);

    adc_oneshot_del_unit(adc);

    int pass = (raw_hi > HIGH_THRESH) && (raw_lo < LOW_THRESH);
    for (int i = 0; i < 10; i++) {
        printf("AEL_GPIOADC raw_hi=%d raw_lo=%d %s\n",
               raw_hi, raw_lo, pass ? "PASS" : "FAIL");
        fflush(stdout);
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
