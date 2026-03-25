#pragma once
/*
 * ael_board_init.h — shared init helpers for ESP32-WROOM-32D test programs.
 *
 * Include this header in every app_main() and call the helpers you need:
 *
 *   ael_common_init()      — always call first: suppresses noisy logs, inits NVS
 *   ael_netif_init()       — before esp_wifi_init() or NimBLE
 *   ael_gpio_isr_init()    — before any gpio_isr_handler_add() or PCNT
 */

#include "nvs_flash.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "driver/gpio.h"
#include "esp_log.h"

/* Suppress noisy IDF logs and initialise NVS flash.
 * Safe to call multiple times (nvs_flash_init is idempotent after first call). */
static inline void ael_common_init(void)
{
    esp_log_level_set("*", ESP_LOG_WARN);
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }
}

/* Initialise TCP/IP stack and default event loop.
 * Required before esp_wifi_init() or any component that posts to the event loop. */
static inline void ael_netif_init(void)
{
    esp_netif_init();
    esp_event_loop_create_default();
}

/* Install the GPIO ISR service.
 * Required before gpio_isr_handler_add() and before pcnt_new_unit(). */
static inline void ael_gpio_isr_init(void)
{
    gpio_install_isr_service(0);
}
