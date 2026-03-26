#include <stdio.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/ble_gap.h"

static SemaphoreHandle_t s_sem;
static volatile int s_adv = 0;

static int _gap_cb(struct ble_gap_event *ev, void *arg)
{
    (void)arg;
    if (ev->type == BLE_GAP_EVENT_DISC)          s_adv++;
    if (ev->type == BLE_GAP_EVENT_DISC_COMPLETE) xSemaphoreGive(s_sem);
    return 0;
}
static void _sync_cb(void)
{
    struct ble_gap_disc_params dp = { .passive=1, .itvl=0x50, .window=0x30 };
    ble_gap_disc(BLE_OWN_ADDR_PUBLIC, 3000, &dp, _gap_cb, NULL);
}
static void _host_task(void *p) { (void)p; nimble_port_run(); nimble_port_freertos_deinit(); }

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

    s_sem = xSemaphoreCreateBinary();
    s_adv = 0;
    nimble_port_init();
    ble_hs_cfg.sync_cb = _sync_cb;
    nimble_port_freertos_init(_host_task);
    xSemaphoreTake(s_sem, pdMS_TO_TICKS(5000));
    int ok = (s_adv > 0);
    printf("AEL_BLE advertisers=%d %s\n", s_adv, ok ? "PASS" : "FAIL");
    nimble_port_stop();
    vTaskDelay(pdMS_TO_TICKS(50));
    nimble_port_deinit();
    fflush(stdout);
}
