/*
 * esp32c5_suite_ext
 *
 * 7-test hardware suite for ESP32-C5:
 *   Temperature, NVS, Wi-Fi dual-band scan, BLE passive scan,
 *   Light sleep, PWM (LEDC self-test), PCNT pulse count.
 *
 * Wiring:
 *   GPIO2 ↔ GPIO3  (PCNT: GPIO2 drives 100 pulses, GPIO3 counts rising edges)
 *   No LA — PWM verified by firmware only.
 *
 * Output tags:
 *   AEL_TEMP, AEL_NVS, AEL_WIFI, AEL_BLE, AEL_SLEEP,
 *   AEL_PWM, AEL_PCNT, AEL_SUITE_EXT DONE
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "driver/pulse_cnt.h"
#include "driver/temperature_sensor.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_sleep.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/ble_gap.h"

/* ── pin assignments ─────────────────────────── */
#define PWM_GPIO    GPIO_NUM_4   /* LEDC output                        */
#define PCNT_DRIVE  GPIO_NUM_2   /* pulse source (jumpered → GPIO3)    */
#define PCNT_INPUT  GPIO_NUM_3   /* PCNT counter input                 */

/* ── LEDC ────────────────────────────────────── */
#define LEDC_TIMER_SEL   LEDC_TIMER_0
#define LEDC_CHAN_SEL    LEDC_CHANNEL_0
#define LEDC_FREQ_HZ     1000
#define LEDC_DUTY_RES    LEDC_TIMER_10_BIT
#define LEDC_DUTY_50PCT  512   /* 50 % of 1024 */

static int s_passed = 0;
static int s_failed = 0;

/* ── microsecond busy-delay ──────────────────── */
static void busy_delay_us(uint32_t us)
{
    int64_t end = esp_timer_get_time() + (int64_t)us;
    while (esp_timer_get_time() < end) {}
}

/* ── 1. Temperature ──────────────────────────── */
static void test_temperature(void)
{
    temperature_sensor_handle_t sensor = NULL;
    temperature_sensor_config_t cfg = TEMPERATURE_SENSOR_CONFIG_DEFAULT(10, 80);
    esp_err_t e = temperature_sensor_install(&cfg, &sensor);
    if (e != ESP_OK) {
        printf("AEL_TEMP install_err=0x%x FAIL\n", e);
        s_failed++; return;
    }
    temperature_sensor_enable(sensor);
    float celsius = 0.0f;
    temperature_sensor_get_celsius(sensor, &celsius);
    temperature_sensor_disable(sensor);
    temperature_sensor_uninstall(sensor);

    int ok = (celsius > 5.0f && celsius < 90.0f);
    printf("AEL_TEMP celsius=%.1f %s\n", celsius, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── 2. NVS ──────────────────────────────────── */
static void test_nvs(void)
{
    const uint32_t WVAL = 0xAE100001U;
    nvs_handle_t h;
    esp_err_t e = nvs_open("ael_test", NVS_READWRITE, &h);
    if (e != ESP_OK) {
        printf("AEL_NVS open_err=0x%x FAIL\n", e);
        s_failed++; return;
    }
    nvs_set_u32(h, "ael_val", WVAL);
    nvs_commit(h);
    uint32_t rval = 0;
    e = nvs_get_u32(h, "ael_val", &rval);
    nvs_close(h);
    int ok = (e == ESP_OK && rval == WVAL);
    printf("AEL_NVS wrote=0x%08lX read=0x%08lX %s\n",
           (unsigned long)WVAL, (unsigned long)rval, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── 3. Wi-Fi dual-band scan ─────────────────── */
static void scan_band(wifi_band_mode_t mode, uint16_t *out)
{
    esp_wifi_set_band_mode(mode);
    wifi_scan_config_t sc = {
        .show_hidden = false,
        .scan_type   = WIFI_SCAN_TYPE_PASSIVE,
    };
    esp_wifi_scan_start(&sc, true);   /* blocking */
    uint16_t cnt = 0;
    esp_wifi_scan_get_ap_num(&cnt);
    if (cnt > 0) {
        wifi_ap_record_t *recs = malloc(cnt * sizeof(wifi_ap_record_t));
        if (recs) {
            uint16_t n = cnt;
            esp_wifi_scan_get_ap_records(&n, recs);
            free(recs);
        }
    }
    *out = cnt;
}

static void test_wifi(void)
{
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();

    uint16_t cnt24 = 0, cnt5 = 0;
    scan_band(WIFI_BAND_MODE_2G_ONLY, &cnt24);
    scan_band(WIFI_BAND_MODE_5G_ONLY, &cnt5);

    esp_wifi_stop();
    esp_wifi_deinit();

    int ok = (cnt24 > 0 || cnt5 > 0);
    printf("AEL_WIFI ap_2g=%u ap_5g=%u %s\n", cnt24, cnt5, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── 4. BLE passive scan ─────────────────────── */
static SemaphoreHandle_t s_ble_sem;
static volatile int      s_ble_adv = 0;

static int _gap_event_cb(struct ble_gap_event *ev, void *arg)
{
    (void)arg;
    if (ev->type == BLE_GAP_EVENT_DISC)          s_ble_adv++;
    if (ev->type == BLE_GAP_EVENT_DISC_COMPLETE) xSemaphoreGive(s_ble_sem);
    return 0;
}

static void _ble_sync_cb(void)
{
    struct ble_gap_disc_params dp = {
        .passive        = 1,
        .itvl           = 0x50,
        .window         = 0x30,
        .filter_policy  = 0,
        .limited        = 0,
        .filter_duplicates = 0,
    };
    ble_gap_disc(BLE_OWN_ADDR_PUBLIC, 3000, &dp, _gap_event_cb, NULL);
}

static void _nimble_host_task(void *p)
{
    (void)p;
    nimble_port_run();
    nimble_port_freertos_deinit();
}

static void test_ble(void)
{
    s_ble_sem = xSemaphoreCreateBinary();
    s_ble_adv = 0;
    nimble_port_init();
    ble_hs_cfg.sync_cb = _ble_sync_cb;
    nimble_port_freertos_init(_nimble_host_task);
    xSemaphoreTake(s_ble_sem, pdMS_TO_TICKS(5000));
    int ok = (s_ble_adv > 0);
    printf("AEL_BLE advertisers=%d %s\n", s_ble_adv, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── 5. Light sleep ──────────────────────────── */
static void test_light_sleep(void)
{
    printf("AEL_SLEEP entering\n");
    fflush(stdout);
    esp_sleep_enable_timer_wakeup(1000000ULL);   /* 1 s */
    esp_light_sleep_start();
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    int ok = (cause == ESP_SLEEP_WAKEUP_TIMER);
    printf("AEL_SLEEP wakeup_cause=%d %s\n", (int)cause, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── 6. PWM (LEDC self-test) ─────────────────── */
static void test_pwm(void)
{
    ledc_timer_config_t tcfg = {
        .speed_mode      = LEDC_LOW_SPEED_MODE,
        .timer_num       = LEDC_TIMER_SEL,
        .duty_resolution = LEDC_DUTY_RES,
        .freq_hz         = LEDC_FREQ_HZ,
        .clk_cfg         = LEDC_AUTO_CLK,
    };
    esp_err_t te = ledc_timer_config(&tcfg);

    ledc_channel_config_t ccfg = {
        .gpio_num   = PWM_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel    = LEDC_CHAN_SEL,
        .timer_sel  = LEDC_TIMER_SEL,
        .duty       = LEDC_DUTY_50PCT,
        .hpoint     = 0,
    };
    esp_err_t ce = ledc_channel_config(&ccfg);

    int ok = (te == ESP_OK && ce == ESP_OK);
    printf("AEL_PWM gpio=GPIO%d freq_hz=%d duty_pct=50 timer_err=%d chan_err=%d %s\n",
           PWM_GPIO, LEDC_FREQ_HZ, (int)te, (int)ce, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
    /* leave PWM running on GPIO4 */
}

/* ── 7. PCNT pulse count ─────────────────────── */
static void test_pcnt(void)
{
    /* configure drive pin */
    gpio_config_t gc = {
        .pin_bit_mask = 1ULL << PCNT_DRIVE,
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc);
    gpio_set_level(PCNT_DRIVE, 0);

    /* configure PCNT unit */
    pcnt_unit_config_t ucfg = {
        .low_limit  = -1,
        .high_limit = 200,
    };
    pcnt_unit_handle_t unit = NULL;
    pcnt_new_unit(&ucfg, &unit);

    pcnt_chan_config_t ccfg = {
        .edge_gpio_num  = PCNT_INPUT,
        .level_gpio_num = -1,
    };
    pcnt_channel_handle_t chan = NULL;
    pcnt_new_channel(unit, &ccfg, &chan);

    pcnt_channel_set_edge_action(chan,
        PCNT_CHANNEL_EDGE_ACTION_INCREASE,
        PCNT_CHANNEL_EDGE_ACTION_HOLD);
    pcnt_channel_set_level_action(chan,
        PCNT_CHANNEL_LEVEL_ACTION_KEEP,
        PCNT_CHANNEL_LEVEL_ACTION_KEEP);

    pcnt_unit_enable(unit);
    pcnt_unit_clear_count(unit);
    pcnt_unit_start(unit);

    const int N = 100;
    for (int i = 0; i < N; i++) {
        gpio_set_level(PCNT_DRIVE, 1);
        busy_delay_us(10);
        gpio_set_level(PCNT_DRIVE, 0);
        busy_delay_us(10);
    }
    vTaskDelay(pdMS_TO_TICKS(10));

    int count = 0;
    pcnt_unit_get_count(unit, &count);
    pcnt_unit_stop(unit);
    pcnt_unit_disable(unit);

    int ok = (count == N);
    printf("AEL_PCNT sent=%d counted=%d %s\n", N, count, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── app_main ────────────────────────────────── */
void app_main(void)
{
    esp_log_level_set("*", ESP_LOG_WARN);

    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }
    esp_netif_init();
    esp_event_loop_create_default();

    vTaskDelay(pdMS_TO_TICKS(2000));
    printf("AEL_SUITE_EXT BOOT\n");
    fflush(stdout);

    test_temperature();
    test_nvs();
    test_wifi();
    test_ble();
    test_light_sleep();
    test_pwm();
    test_pcnt();

    printf("AEL_SUITE_EXT DONE passed=%d failed=%d\n", s_passed, s_failed);
    fflush(stdout);
}
