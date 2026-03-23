/*
 * esp32c5_nvs_readwrite
 *
 * Writes a known 32-bit value to NVS, reads it back, and compares.
 * No wiring required.
 *
 * Patterns (on UART0 bridge, /dev/ttyACM0):
 *   AEL_NVS PASS val=0xdeadbeef   — write/read roundtrip succeeded
 *   AEL_NVS FAIL ...              — mismatch or driver error
 */

#include <stdio.h>
#include "nvs_flash.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define NVS_NS    "ael_test"
#define NVS_KEY   "ael_val"
#define TEST_VAL  0xDEADBEEFU

void app_main(void)
{
    /* Wait for UART observer to connect before producing output */
    vTaskDelay(pdMS_TO_TICKS(2000));

    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        ret = nvs_flash_init();
    }
    if (ret != ESP_OK) {
        printf("AEL_NVS FAIL nvs_flash_init err=0x%x\n", ret);
        return;
    }

    nvs_handle_t h;
    ret = nvs_open(NVS_NS, NVS_READWRITE, &h);
    if (ret != ESP_OK) {
        printf("AEL_NVS FAIL nvs_open err=0x%x\n", ret);
        return;
    }

    nvs_set_u32(h, NVS_KEY, TEST_VAL);
    nvs_commit(h);

    uint32_t val = 0;
    ret = nvs_get_u32(h, NVS_KEY, &val);
    nvs_close(h);

    const char *result = (ret == ESP_OK && val == TEST_VAL) ? "PASS" : "FAIL";
    /* Print result several times so observer can catch it */
    for (int i = 0; i < 5; i++) {
        if (ret == ESP_OK && val == TEST_VAL) {
            printf("AEL_NVS PASS val=0x%08lx\n", (unsigned long)val);
        } else {
            printf("AEL_NVS FAIL ret=0x%x expected=0x%08lx got=0x%08lx\n",
                   ret, (unsigned long)TEST_VAL, (unsigned long)val);
        }
        vTaskDelay(pdMS_TO_TICKS(500));
    }
    (void)result;
}
