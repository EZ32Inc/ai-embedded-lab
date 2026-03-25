/*
 * test_nvs — Stage 1: NVS read/write self-test (no external wiring)
 *
 * Writes a known u32 to NVS and reads it back.
 * Output: AEL_NVS wrote=0x... read=0x... PASS|FAIL
 */

#include <stdio.h>
#include "ael_board_init.h"
#include "nvs.h"

void app_main(void)
{
    ael_common_init();

    const uint32_t WVAL = 0xAE320001U;
    nvs_handle_t h;
    esp_err_t e = nvs_open("ael_esp32", NVS_READWRITE, &h);
    if (e != ESP_OK) {
        printf("AEL_NVS open_err=0x%x FAIL\n", e);
        return;
    }
    nvs_set_u32(h, "ael_val", WVAL);
    nvs_commit(h);
    uint32_t rval = 0;
    e = nvs_get_u32(h, "ael_val", &rval);
    nvs_close(h);

    int ok = (e == ESP_OK && rval == WVAL);
    printf("AEL_NVS wrote=0x%08lX read=0x%08lX %s\n",
           (unsigned long)WVAL, (unsigned long)rval, ok ? "PASS" : "FAIL");
}
