#include <stdio.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "driver/gpio.h"
#include "esp_netif.h"
#include "esp_event.h"

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

    const uint32_t WVAL = 0xAE100005U;
    nvs_handle_t h;
    esp_err_t e = nvs_open("ael_c5", NVS_READWRITE, &h);
    if (e != ESP_OK) { printf("AEL_NVS open_err=0x%x FAIL\n", e); return; }
    nvs_set_u32(h, "ael_val", WVAL);
    nvs_commit(h);
    uint32_t rval = 0;
    e = nvs_get_u32(h, "ael_val", &rval);
    nvs_close(h);
    int ok = (e == ESP_OK && rval == WVAL);
    printf("AEL_NVS wrote=0x%08lX read=0x%08lX %s\n",
           (unsigned long)WVAL, (unsigned long)rval, ok ? "PASS" : "FAIL");
    fflush(stdout);
}
