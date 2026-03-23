/*
 * esp32c5_wifi_dual_band
 *
 * Scans 2.4 GHz and 5 GHz bands separately and prints AP counts.
 * No wiring required. ESP32-C5 is the only ESP32 with dual-band WiFi.
 *
 * Patterns (on UART0 bridge, /dev/ttyACM0):
 *   AEL_WIFI2G FOUND:<n>   — APs found on 2.4 GHz scan
 *   AEL_WIFI5G FOUND:<n>   — APs found on 5 GHz scan
 *   AEL_WIFI DONE          — both scans complete
 */

#include <stdio.h>
#include <string.h>
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_netif.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static void scan_band(wifi_band_mode_t mode, const char *tag)
{
    esp_wifi_set_band_mode(mode);

    wifi_scan_config_t scan_cfg = {
        .show_hidden = false,
        .scan_type   = WIFI_SCAN_TYPE_ACTIVE,
    };
    esp_wifi_scan_start(&scan_cfg, true);   /* blocking */

    uint16_t count = 0;
    esp_wifi_scan_get_ap_num(&count);

    /* Drain the list so internal memory is freed */
    if (count > 0) {
        wifi_ap_record_t *recs = malloc(count * sizeof(wifi_ap_record_t));
        if (recs) {
            uint16_t n = count;
            esp_wifi_scan_get_ap_records(&n, recs);
            free(recs);
        }
    }

    printf("%s FOUND:%u\n", tag, (unsigned)count);
}

void app_main(void)
{
    /* NVS required by WiFi driver */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();

    scan_band(WIFI_BAND_MODE_2G_ONLY, "AEL_WIFI2G");
    scan_band(WIFI_BAND_MODE_5G_ONLY, "AEL_WIFI5G");

    printf("AEL_WIFI DONE\n");

    esp_wifi_stop();
    esp_wifi_deinit();
}
