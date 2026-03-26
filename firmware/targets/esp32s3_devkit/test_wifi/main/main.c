/* test_wifi — Stage 1: Wi-Fi passive scan (2.4 GHz). No wiring required.
 * ESP32-S3 is 2.4 GHz only — no esp_wifi_set_band_mode() needed. */
#include <stdio.h>
#include <stdlib.h>
#include "ael_board_init.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void app_main(void)
{
    ael_common_init();
    ael_netif_init();
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t wcfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&wcfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();
    wifi_scan_config_t scfg = { .show_hidden = false, .scan_type = WIFI_SCAN_TYPE_PASSIVE };
    esp_wifi_scan_start(&scfg, true);
    uint16_t ap_count = 0;
    esp_wifi_scan_get_ap_num(&ap_count);
    if (ap_count > 0) {
        wifi_ap_record_t *recs = malloc(ap_count * sizeof(wifi_ap_record_t));
        if (recs) { uint16_t n = ap_count; esp_wifi_scan_get_ap_records(&n, recs); free(recs); }
    }
    esp_wifi_stop();
    esp_wifi_deinit();
    int ok = (ap_count >= 1);
    printf("AEL_WIFI ap_2g=%u %s\n", (unsigned)ap_count, ok ? "PASS" : "FAIL");
    while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
}
