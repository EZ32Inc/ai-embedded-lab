/* test_wifi — Stage 1: Wi-Fi passive scan (2.4 GHz). No wiring required. */
#include <stdio.h>
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
    wifi_scan_config_t scfg = { .scan_type = WIFI_SCAN_TYPE_PASSIVE };
    esp_wifi_scan_start(&scfg, true);
    uint16_t ap_count = 0;
    esp_wifi_scan_get_ap_num(&ap_count);
    esp_wifi_stop();
    esp_wifi_deinit();
    int ok = (ap_count >= 1);
    printf("AEL_WIFI ap_count=%u %s\n", (unsigned)ap_count, ok ? "PASS" : "FAIL");
    while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
}
