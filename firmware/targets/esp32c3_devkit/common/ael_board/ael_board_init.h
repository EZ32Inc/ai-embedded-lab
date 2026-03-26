#pragma once
#include "driver/gpio.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "nvs_flash.h"

/* ESP32-C3 DevKit (native USB / USB Serial JTAG console).
 * Call ael_common_init() before esp_wifi_init() or nimble_port_init(). */
static inline void ael_gpio_isr_init(void)
{
    gpio_install_isr_service(0);
}

static inline void ael_common_init(void)
{
    esp_log_level_set("*", ESP_LOG_WARN);
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }
}

static inline void ael_netif_init(void)
{
    esp_netif_init();
    esp_event_loop_create_default();
}
