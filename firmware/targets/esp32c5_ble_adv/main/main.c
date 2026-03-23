/*
 * esp32c5_ble_adv
 *
 * Initialises NimBLE and starts non-connectable BLE advertising.
 * Prints PASS once advertising is confirmed active.
 * No wiring required.
 *
 * Patterns (on UART0 bridge, /dev/ttyACM0):
 *   AEL_BLE ADV_STARTED   — advertising started successfully
 *   AEL_BLE PASS          — advertising confirmed, test complete
 *   AEL_BLE ADV_FAIL ...  — ble_gap_adv_start returned error
 */

#include <stdio.h>
#include "nvs_flash.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "services/gap/ble_svc_gap.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static volatile int adv_started = 0;

static void ble_app_on_sync(void)
{
    struct ble_gap_adv_params adv_params = {0};
    adv_params.conn_mode = BLE_GAP_CONN_MODE_NON;
    adv_params.disc_mode = BLE_GAP_DISC_MODE_GEN;

    int rc = ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER,
                               &adv_params, NULL, NULL);
    if (rc == 0) {
        printf("AEL_BLE ADV_STARTED\n");
        adv_started = 1;
    } else {
        printf("AEL_BLE ADV_FAIL rc=%d\n", rc);
    }
}

static void nimble_host_task(void *param)
{
    nimble_port_run();
    nimble_port_freertos_deinit();
}

void app_main(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    nimble_port_init();
    ble_hs_cfg.sync_cb = ble_app_on_sync;
    ble_svc_gap_init();
    ble_svc_gap_device_name_set("AEL-C5");
    nimble_port_freertos_init(nimble_host_task);

    /* Wait up to 5 s for advertising to start */
    for (int i = 0; i < 50 && !adv_started; i++) {
        vTaskDelay(pdMS_TO_TICKS(100));
    }

    if (adv_started) {
        vTaskDelay(pdMS_TO_TICKS(2000));   /* let it advertise briefly */
        printf("AEL_BLE PASS\n");
    } else {
        printf("AEL_BLE FAIL timeout waiting for sync\n");
    }
}
