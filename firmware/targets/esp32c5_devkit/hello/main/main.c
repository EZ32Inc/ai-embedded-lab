#include <stdio.h>
#include "esp_log.h"
#include "nvs_flash.h"

void app_main(void)
{
    esp_log_level_set("*", ESP_LOG_WARN);
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase(); nvs_flash_init();
    }
    printf("AEL_HELLO board=ESP32C5 PASS\n");
    fflush(stdout);
}
