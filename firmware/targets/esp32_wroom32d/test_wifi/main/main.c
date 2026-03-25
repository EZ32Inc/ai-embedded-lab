/*
 * test_wifi — Stage 1: 2.4 GHz passive scan (no external wiring)
 *
 * Scans for APs and passes if at least one is found.
 * Output: AEL_WIFI ap_2g=N PASS|FAIL
 *
 * Note: ESP32 classic supports 2.4 GHz only; no esp_wifi_set_band_mode().
 *       ADC2 is unavailable during WiFi; all ADC tests must use ADC1.
 */

#include <stdio.h>
#include <stdlib.h>
#include "ael_board_init.h"
#include "esp_wifi.h"

void app_main(void)
{
    ael_common_init();
    ael_netif_init();

    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();

    wifi_scan_config_t sc = { .show_hidden = false, .scan_type = WIFI_SCAN_TYPE_PASSIVE };
    esp_wifi_scan_start(&sc, true);

    uint16_t cnt = 0;
    esp_wifi_scan_get_ap_num(&cnt);
    if (cnt > 0) {
        wifi_ap_record_t *recs = malloc(cnt * sizeof(wifi_ap_record_t));
        if (recs) {
            uint16_t n = cnt;
            esp_wifi_scan_get_ap_records(&n, recs);
            free(recs);
        }
    }

    esp_wifi_stop();
    esp_wifi_deinit();

    int ok = (cnt > 0);
    printf("AEL_WIFI ap_2g=%u %s\n", cnt, ok ? "PASS" : "FAIL");
}
