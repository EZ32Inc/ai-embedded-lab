#pragma once
#include "nvs_flash.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "driver/gpio.h"

static inline void ael_common_init(void) {
    /* GPIO ISR service MUST be installed before WiFi/BLE (CE dbdf36fb):
     * If BLE allocates the dispatch table first it lands in IRAM which is
     * execute-only on C5 (PMP_IDRAM_SPLIT=y), causing Store access fault. */
    gpio_install_isr_service(0);

    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase(); nvs_flash_init();
    }
    esp_netif_init();
    esp_event_loop_create_default();
}
