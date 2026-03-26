/* test_nvs — Stage 1: NVS write/read. No wiring required. */
#include <stdio.h>
#include "ael_board_init.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void app_main(void)
{
    ael_common_init();
    const uint32_t WVAL = 0xAE1C0001U;
    nvs_handle_t h;
    esp_err_t e = nvs_open("ael_esp32c3", NVS_READWRITE, &h);
    if (e != ESP_OK) { printf("AEL_NVS open_err=0x%x FAIL\n", e); return; }
    nvs_set_u32(h, "ael_val", WVAL);
    nvs_commit(h);
    uint32_t rval = 0;
    e = nvs_get_u32(h, "ael_val", &rval);
    nvs_close(h);
    int ok = (e == ESP_OK && rval == WVAL);
    printf("AEL_NVS wrote=0x%08lX read=0x%08lX %s\n",
           (unsigned long)WVAL, (unsigned long)rval, ok ? "PASS" : "FAIL");
    while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
}
