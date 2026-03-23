/*
 * esp32c6_suite_ext — Extended hardware verification suite
 *
 * Seven tests executed sequentially; results reported on UART0 (115200 8N1).
 *
 * Connections (reuse existing bench wiring):
 *   GPIO20 <--> GPIO21   jumper — PCNT pulse count
 *   GPIO3  -->  LA P0.1         — PWM observation (no extra wire)
 *   LA wires GPIO2/3/5/6 unchanged.
 *
 * Tests:
 *   AEL_TEMP   internal temperature sensor     (no wiring)
 *   AEL_NVS    NVS flash write/read             (no wiring)
 *   AEL_WIFI   Wi-Fi AP passive scan ≥1 AP      (no wiring)
 *   AEL_BLE    BLE passive scan ≥1 advertiser   (no wiring)
 *   AEL_SLEEP  light sleep 1 s, timer wakeup    (no wiring)
 *   AEL_PWM    LEDC 1 kHz 50% on GPIO3 (P0.1)  (no wiring)
 *   AEL_PCNT   100 pulses GPIO20→GPIO21          (existing jumper)
 *
 * Post-test: GPIO3 stays on LEDC 1 kHz for LA duty/freq measurement.
 *            GPIO5/6 toggle manually for LA edge-count confirmation.
 */

#include <stdio.h>
#include <string.h>
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "driver/pulse_cnt.h"
#include "driver/temperature_sensor.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_sleep.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "nvs.h"
#include "nvs_flash.h"

/* NimBLE */
#include "host/ble_gap.h"
#include "host/ble_hs.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"


/* ------------------------------------------------------------------ */
/* GPIO helpers                                                        */
/* ------------------------------------------------------------------ */

static void gpio_as_out(gpio_num_t pin)
{
    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << pin,
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
}

static void gpio_as_in(gpio_num_t pin)
{
    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << pin,
        .mode         = GPIO_MODE_INPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
}

static void busy_delay_us(uint32_t us)
{
    uint64_t t = esp_timer_get_time();
    while ((esp_timer_get_time() - t) < (uint64_t)us);
}

/* ------------------------------------------------------------------ */
/* Test 1: Internal temperature sensor                                 */
/* ------------------------------------------------------------------ */

static void test_temperature(int *passed, int *failed)
{
    temperature_sensor_handle_t ts = NULL;
    temperature_sensor_config_t cfg = TEMPERATURE_SENSOR_CONFIG_DEFAULT(10, 80);
    esp_err_t err = temperature_sensor_install(&cfg, &ts);
    if (err != ESP_OK) {
        (*failed)++;
        printf("AEL_TEMP err=%d FAIL\n", (int)err);
        fflush(stdout);
        return;
    }
    temperature_sensor_enable(ts);
    float celsius = 0.0f;
    temperature_sensor_get_celsius(ts, &celsius);
    temperature_sensor_disable(ts);
    temperature_sensor_uninstall(ts);

    int ok = (celsius > 10.0f) && (celsius < 85.0f);
    if (ok) (*passed)++; else (*failed)++;
    printf("AEL_TEMP celsius=%.1f %s\n", celsius, ok ? "PASS" : "FAIL");
    fflush(stdout);
}

/* ------------------------------------------------------------------ */
/* Test 2: NVS flash write / read                                      */
/* ------------------------------------------------------------------ */

static void test_nvs(int *passed, int *failed)
{
    nvs_handle_t h;
    esp_err_t err = nvs_open("ael_test", NVS_READWRITE, &h);
    if (err != ESP_OK) {
        (*failed)++;
        printf("AEL_NVS open_err=%d FAIL\n", (int)err);
        fflush(stdout);
        return;
    }
    const uint32_t MAGIC = 0xAE100001UL;
    nvs_set_u32(h, "magic", MAGIC);
    nvs_commit(h);
    uint32_t val = 0;
    nvs_get_u32(h, "magic", &val);
    nvs_close(h);

    int ok = (val == MAGIC);
    if (ok) (*passed)++; else (*failed)++;
    printf("AEL_NVS wrote=0x%08X read=0x%08X %s\n",
           (unsigned)MAGIC, (unsigned)val, ok ? "PASS" : "FAIL");
    fflush(stdout);
}

/* ------------------------------------------------------------------ */
/* Test 3: Wi-Fi AP scan                                               */
/* ------------------------------------------------------------------ */

static void test_wifi_scan(int *passed, int *failed)
{
    esp_netif_t *sta = esp_netif_create_default_wifi_sta();

    wifi_init_config_t wcfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&wcfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();

    wifi_scan_config_t scfg = { .scan_type = WIFI_SCAN_TYPE_PASSIVE };
    esp_wifi_scan_start(&scfg, true);   /* blocking */

    uint16_t ap_count = 0;
    esp_wifi_scan_get_ap_num(&ap_count);

    esp_wifi_stop();
    esp_wifi_deinit();
    esp_netif_destroy(sta);

    int ok = (ap_count > 0);
    if (ok) (*passed)++; else (*failed)++;
    printf("AEL_WIFI ap_count=%u %s\n", (unsigned)ap_count, ok ? "PASS" : "FAIL");
    fflush(stdout);
}

/* ------------------------------------------------------------------ */
/* Test 4: BLE passive scan (NimBLE)                                   */
/* ------------------------------------------------------------------ */

static SemaphoreHandle_t s_ble_sem;
static volatile int      s_ble_found;

static int _gap_event_cb(struct ble_gap_event *ev, void *arg)
{
    if (ev->type == BLE_GAP_EVENT_DISC) {
        s_ble_found++;
    } else if (ev->type == BLE_GAP_EVENT_DISC_COMPLETE) {
        xSemaphoreGive(s_ble_sem);
    }
    return 0;
}

static void _ble_on_sync(void)
{
    struct ble_gap_disc_params dp = {
        .passive          = 1,
        .itvl             = 0x0100,   /* 160 ms */
        .window           = 0x0080,   /*  80 ms */
        .filter_policy    = BLE_HCI_SCAN_FILT_NO_WL,
        .limited          = 0,
        .filter_duplicates = 0,
    };
    ble_gap_disc(BLE_OWN_ADDR_PUBLIC, 3000, &dp, _gap_event_cb, NULL);
}

static void _ble_on_reset(int reason) { (void)reason; }

static void _ble_host_task(void *arg)
{
    nimble_port_run();
    nimble_port_freertos_deinit();
}

static void test_ble_scan(int *passed, int *failed)
{
    s_ble_sem   = xSemaphoreCreateBinary();
    s_ble_found = 0;

    nimble_port_init();
    ble_hs_cfg.sync_cb  = _ble_on_sync;
    ble_hs_cfg.reset_cb = _ble_on_reset;
    nimble_port_freertos_init(_ble_host_task);

    /* Wait up to 5 s for scan to complete (3 s scan + margin) */
    xSemaphoreTake(s_ble_sem, pdMS_TO_TICKS(5000));

    nimble_port_stop();
    vTaskDelay(pdMS_TO_TICKS(300));   /* let host task exit cleanly */
    nimble_port_deinit();
    vSemaphoreDelete(s_ble_sem);

    int ok = (s_ble_found > 0);
    if (ok) (*passed)++; else (*failed)++;
    printf("AEL_BLE advertisers=%d %s\n", s_ble_found, ok ? "PASS" : "FAIL");
    fflush(stdout);
}

/* ------------------------------------------------------------------ */
/* Test 5: Light sleep + timer wakeup                                  */
/* ------------------------------------------------------------------ */

static void test_light_sleep(int *passed, int *failed)
{
    printf("AEL_SLEEP entering\n"); fflush(stdout);
    vTaskDelay(pdMS_TO_TICKS(50));   /* flush UART TX */

    esp_sleep_enable_timer_wakeup(1000000ULL);   /* 1 second */
    esp_light_sleep_start();

    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    int ok = (cause == ESP_SLEEP_WAKEUP_TIMER);
    if (ok) (*passed)++; else (*failed)++;
    printf("AEL_SLEEP wakeup_cause=%d %s\n", (int)cause, ok ? "PASS" : "FAIL");
    fflush(stdout);
}

/* ------------------------------------------------------------------ */
/* Test 6: LEDC PWM on GPIO3 (LA P0.1) @ 1 kHz, 50% duty             */
/* ------------------------------------------------------------------ */

static void test_pwm(int *passed, int *failed)
{
    ledc_timer_config_t tc = {
        .speed_mode      = LEDC_LOW_SPEED_MODE,
        .duty_resolution = LEDC_TIMER_10_BIT,   /* 0-1023 */
        .timer_num       = LEDC_TIMER_0,
        .freq_hz         = 1000,
        .clk_cfg         = LEDC_AUTO_CLK,
    };
    esp_err_t te = ledc_timer_config(&tc);

    ledc_channel_config_t cc = {
        .gpio_num   = GPIO_NUM_3,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel    = LEDC_CHANNEL_0,
        .timer_sel  = LEDC_TIMER_0,
        .duty       = 512,   /* 50% of 1024 */
        .hpoint     = 0,
    };
    esp_err_t ce = ledc_channel_config(&cc);

    int ok = (te == ESP_OK) && (ce == ESP_OK);
    if (ok) (*passed)++; else (*failed)++;
    printf("AEL_PWM gpio=GPIO3 freq_hz=1000 duty_pct=50 timer_err=%d chan_err=%d %s\n",
           (int)te, (int)ce, ok ? "PASS" : "FAIL");
    fflush(stdout);
    /* LEDC keeps running — LA will observe the 1 kHz signal post-DONE */
}

/* ------------------------------------------------------------------ */
/* Test 7: PCNT — 100 pulses GPIO20 → GPIO21 (existing jumper)        */
/* ------------------------------------------------------------------ */

#define PULSE_GPIO   GPIO_NUM_20
#define PCNT_GPIO    GPIO_NUM_21
#define PULSE_COUNT  100

static void test_pcnt(int *passed, int *failed)
{
    /* PCNT unit */
    pcnt_unit_config_t uc = { .high_limit = PULSE_COUNT + 10, .low_limit = -1 };
    pcnt_unit_handle_t unit = NULL;
    pcnt_new_unit(&uc, &unit);

    /* PCNT channel: count rising edges on GPIO21 */
    pcnt_chan_config_t cc = {
        .edge_gpio_num  = PCNT_GPIO,
        .level_gpio_num = -1,           /* unused */
    };
    pcnt_channel_handle_t chan = NULL;
    pcnt_new_channel(unit, &cc, &chan);
    pcnt_channel_set_edge_action(chan,
        PCNT_CHANNEL_EDGE_ACTION_INCREASE,   /* rising  → count++ */
        PCNT_CHANNEL_EDGE_ACTION_HOLD);      /* falling → hold    */

    pcnt_unit_enable(unit);
    pcnt_unit_clear_count(unit);
    pcnt_unit_start(unit);

    /* Generate PULSE_COUNT pulses on GPIO20 */
    gpio_as_out(PULSE_GPIO);
    gpio_as_in(PCNT_GPIO);   /* high-Z input for PCNT */
    gpio_set_level(PULSE_GPIO, 0);
    for (int i = 0; i < PULSE_COUNT; i++) {
        gpio_set_level(PULSE_GPIO, 1);
        busy_delay_us(10);
        gpio_set_level(PULSE_GPIO, 0);
        busy_delay_us(10);
    }
    vTaskDelay(pdMS_TO_TICKS(10));

    int count = 0;
    pcnt_unit_get_count(unit, &count);

    pcnt_unit_stop(unit);
    pcnt_unit_disable(unit);
    pcnt_del_channel(chan);
    pcnt_del_unit(unit);

    int ok = (count == PULSE_COUNT);
    if (ok) (*passed)++; else (*failed)++;
    printf("AEL_PCNT sent=%d counted=%d %s\n",
           PULSE_COUNT, count, ok ? "PASS" : "FAIL");
    fflush(stdout);
}

/* ------------------------------------------------------------------ */
/* app_main                                                            */
/* ------------------------------------------------------------------ */

void app_main(void)
{
    esp_task_wdt_deinit();
    esp_log_level_set("*", ESP_LOG_WARN);   /* suppress IDF noise during tests */
    vTaskDelay(pdMS_TO_TICKS(2000));
    printf("AEL_SUITE_EXT BOOT\n"); fflush(stdout);

    /* Shared init (required by Wi-Fi; also used by NVS test) */
    esp_err_t nvs_err = nvs_flash_init();
    if (nvs_err == ESP_ERR_NVS_NO_FREE_PAGES || nvs_err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }
    esp_netif_init();
    esp_event_loop_create_default();

    int passed = 0, failed = 0;

    test_temperature(&passed, &failed);
    test_nvs(&passed, &failed);
    test_wifi_scan(&passed, &failed);
    test_ble_scan(&passed, &failed);
    test_light_sleep(&passed, &failed);
    test_pwm(&passed, &failed);
    test_pcnt(&passed, &failed);

    printf("AEL_SUITE_EXT DONE passed=%d failed=%d\n", passed, failed);
    fflush(stdout);

    /* Post-test observation loop:
     *   GPIO3 → already running LEDC 1 kHz (LA P0.1 measures PWM)
     *   GPIO5/6 → manual toggle for edge-count baseline (LA P0.2/P0.3) */
    gpio_as_out(GPIO_NUM_5);
    gpio_as_out(GPIO_NUM_6);

    int64_t now        = esp_timer_get_time();
    int64_t next5      = now +  5000;
    int64_t next6      = now +  2500;
    int64_t last_print = now;
    int64_t last_yield = now;
    uint8_t s5 = 0, s6 = 0;

    while (1) {
        now = esp_timer_get_time();
        if (now >= next5) { next5 +=  5000; s5 ^= 1; gpio_set_level(GPIO_NUM_5, s5); }
        if (now >= next6) { next6 +=  2500; s6 ^= 1; gpio_set_level(GPIO_NUM_6, s6); }
        if (now - last_print >= 3000000LL) {
            last_print = now;
            printf("AEL_SUITE_EXT RUNNING\n"); fflush(stdout);
        }
        if (now - last_yield >= 5000) { last_yield = now; taskYIELD(); }
    }
}
