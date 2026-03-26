/* test_ble — Stage 1: BLE passive scan (NimBLE). No wiring required. */
#include <stdio.h>
#include "ael_board_init.h"
#include "host/ble_gap.h"
#include "host/ble_hs.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

static SemaphoreHandle_t s_sem;
static volatile int      s_adv_count = 0;

static int _gap_cb(struct ble_gap_event *ev, void *arg)
{
    (void)arg;
    if (ev->type == BLE_GAP_EVENT_DISC)          s_adv_count++;
    if (ev->type == BLE_GAP_EVENT_DISC_COMPLETE) xSemaphoreGive(s_sem);
    return 0;
}

static void _sync_cb(void)
{
    struct ble_gap_disc_params dp = {
        .passive = 1, .itvl = 0x50, .window = 0x30,
        .filter_policy = 0, .limited = 0, .filter_duplicates = 0,
    };
    ble_gap_disc(BLE_OWN_ADDR_PUBLIC, 3000, &dp, _gap_cb, NULL);
}

static void _host_task(void *p) { (void)p; nimble_port_run(); nimble_port_freertos_deinit(); }

void app_main(void)
{
    ael_common_init();
    s_sem = xSemaphoreCreateBinary();
    nimble_port_init();
    ble_hs_cfg.sync_cb = _sync_cb;
    nimble_port_freertos_init(_host_task);
    xSemaphoreTake(s_sem, pdMS_TO_TICKS(5000));
    int ok = (s_adv_count > 0);
    printf("AEL_BLE advertisers=%d %s\n", s_adv_count, ok ? "PASS" : "FAIL");
    nimble_port_stop();
    vTaskDelay(pdMS_TO_TICKS(50));
    nimble_port_deinit();
    while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
}
