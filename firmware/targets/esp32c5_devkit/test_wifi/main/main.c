#include <stdio.h>
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "nvs_flash.h"
#include "driver/gpio.h"

void app_main(void)
{
    esp_log_level_set("*", ESP_LOG_WARN);
    gpio_install_isr_service(0);
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase(); nvs_flash_init();
    }
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();

    /* Dual-band scan: C5 supports 2.4GHz + 5GHz */
    esp_wifi_set_band_mode(WIFI_BAND_MODE_2G_ONLY);
    wifi_scan_config_t sc = { .show_hidden = false, .scan_type = WIFI_SCAN_TYPE_PASSIVE };
    esp_wifi_scan_start(&sc, true);
    uint16_t cnt24 = 0;
    esp_wifi_scan_get_ap_num(&cnt24);

    esp_wifi_set_band_mode(WIFI_BAND_MODE_5G_ONLY);
    esp_wifi_scan_start(&sc, true);
    uint16_t cnt5 = 0;
    esp_wifi_scan_get_ap_num(&cnt5);

    esp_wifi_stop();
    esp_wifi_deinit();

    int ok = (cnt24 > 0 || cnt5 > 0);
    printf("AEL_WIFI ap_2g=%u ap_5g=%u %s\n", cnt24, cnt5, ok ? "PASS" : "FAIL");
    fflush(stdout);
}
