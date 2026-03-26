/* test_full_suite — ESP32-C5 DevKit Rule-B convenience layer
 * Runs 12 sub-tests in sequence:
 *   hello, nvs, temp, wifi, ble, sleep, pwm, gpio_intr, pcnt, uart, adc, spi
 * Expected output: AEL_SUITE_FULL DONE passed=12 failed=0
 *
 * NOTE: I2C (test_i2c) excluded — ESP32-C5 I2C V2 slave does not drive ACK
 * when addressed by bit-bang master despite correct GPIO matrix config.
 * Wires GPIO8<->GPIO14, GPIO13<->GPIO23 remain on bench but are unused here.
 * See docs/esp32c5_closeout_report.md for full investigation notes.
 *
 * Wiring (4 jumpers required):
 *   GPIO2  <-> GPIO3    PCNT / GPIO interrupt (shared)
 *   GPIO4  <-> GPIO5    UART1 TX/RX loopback
 *   GPIO6  ->  GPIO1    ADC drive -> ADC1_CH0
 *   GPIO7  <-> GPIO9    SPI2 MOSI <-> MISO loopback
 *
 * ESP32-C5 specific lessons applied (from CE):
 *   - IRAM_ATTR on ISR function only; volatile variables in DRAM
 *     (IRAM is execute-only with CONFIG_ESP_SYSTEM_PMP_IDRAM_SPLIT=y)
 *   - gpio_install_isr_service(0) called before WiFi/BLE init (CE dbdf36fb)
 *   - CONFIG_ESP_MAIN_TASK_STACK_SIZE=8192 in sdkconfig.defaults (CE 73f41c63)
 *   - test_gpio_intr runs before test_pcnt — shared GPIO2/GPIO3 (CE 92297155)
 *   - do NOT call pcnt_del_* after test_pcnt — panics on v5.5.2
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
#include "driver/uart.h"
#include "driver/spi_master.h"
#include "esp_timer.h"
#include "driver/temperature_sensor.h"
#include "esp_adc/adc_oneshot.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_sleep.h"
#include "esp_log.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/ble_gap.h"

/* ── pin assignments ─────────────────────────── */
#define PCNT_DRIVE   GPIO_NUM_2
#define PCNT_INPUT   GPIO_NUM_3
#define INTR_DRIVE   GPIO_NUM_2
#define INTR_INPUT   GPIO_NUM_3

#define UART1_TX     GPIO_NUM_4
#define UART1_RX     GPIO_NUM_5

#define ADC_DRIVE    GPIO_NUM_6
#define ADC_UNIT     ADC_UNIT_1
#define ADC_CHAN     ADC_CHANNEL_0   /* GPIO1 = ADC1_CH0 on ESP32-C5 */
#define ADC_ATTEN    ADC_ATTEN_DB_12
#define ADC_HI_THRESH 2000
#define ADC_LO_THRESH  500

#define SPI_HOST_SEL SPI2_HOST
#define PIN_MOSI     GPIO_NUM_7
#define PIN_MISO     GPIO_NUM_9
#define PIN_CLK      GPIO_NUM_0
#define PIN_CS       GPIO_NUM_10

#define PWM_GPIO     GPIO_NUM_15

static int s_passed = 0;
static int s_failed = 0;

static void busy_delay_us(uint32_t us)
{
    int64_t end = esp_timer_get_time() + (int64_t)us;
    while (esp_timer_get_time() < end) {}
}

/* ── 0. Hello ────────────────────────────────── */
static void sub_hello(void)
{
    printf("AEL_HELLO board=ESP32C5 PASS\n");
    s_passed++;
}

/* ── 1. Temperature ──────────────────────────── */
static void test_temperature(void)
{
    temperature_sensor_handle_t sensor = NULL;
    temperature_sensor_config_t cfg = TEMPERATURE_SENSOR_CONFIG_DEFAULT(10, 80);
    esp_err_t e = temperature_sensor_install(&cfg, &sensor);
    if (e != ESP_OK) { printf("AEL_TEMP install_err=0x%x FAIL\n", e); s_failed++; return; }
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
    const uint32_t WVAL = 0xAE100005U;
    nvs_handle_t h;
    esp_err_t e = nvs_open("ael_c5", NVS_READWRITE, &h);
    if (e != ESP_OK) { printf("AEL_NVS open_err=0x%x FAIL\n", e); s_failed++; return; }
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
    wifi_scan_config_t sc = { .show_hidden = false, .scan_type = WIFI_SCAN_TYPE_PASSIVE };
    esp_wifi_scan_start(&sc, true);
    uint16_t cnt = 0;
    esp_wifi_scan_get_ap_num(&cnt);
    if (cnt > 0) {
        wifi_ap_record_t *recs = malloc(cnt * sizeof(wifi_ap_record_t));
        if (recs) { uint16_t n = cnt; esp_wifi_scan_get_ap_records(&n, recs); free(recs); }
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
        .passive = 1, .itvl = 0x50, .window = 0x30,
        .filter_policy = 0, .limited = 0, .filter_duplicates = 0,
    };
    ble_gap_disc(BLE_OWN_ADDR_PUBLIC, 3000, &dp, _gap_event_cb, NULL);
}
static void _nimble_host_task(void *p) { (void)p; nimble_port_run(); nimble_port_freertos_deinit(); }

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

    /* Stop NimBLE host and BT controller.
     * NimBLE host task runs at high priority; leaving it running preempts the
     * I2C bit-bang slave task, causing it to miss the START condition.
     * Stopping here lets the slave task run uncontested. */
    nimble_port_stop();
    vTaskDelay(pdMS_TO_TICKS(50));   /* let host task call nimble_port_freertos_deinit() */
    nimble_port_deinit();
}

/* ── 5. Light sleep ──────────────────────────── */
static void test_light_sleep(void)
{
    printf("AEL_SLEEP entering\n"); fflush(stdout);
    esp_sleep_enable_timer_wakeup(1000000ULL);
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
        .speed_mode = LEDC_LOW_SPEED_MODE, .timer_num = LEDC_TIMER_0,
        .duty_resolution = LEDC_TIMER_10_BIT, .freq_hz = 1000, .clk_cfg = LEDC_AUTO_CLK,
    };
    esp_err_t te = ledc_timer_config(&tcfg);
    ledc_channel_config_t ccfg = {
        .gpio_num = PWM_GPIO, .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_0, .timer_sel = LEDC_TIMER_0, .duty = 512, .hpoint = 0,
    };
    esp_err_t ce = ledc_channel_config(&ccfg);
    int ok = (te == ESP_OK && ce == ESP_OK);
    printf("AEL_PWM gpio=GPIO%d freq_hz=1000 duty_pct=50 timer_err=%d chan_err=%d %s\n",
           PWM_GPIO, (int)te, (int)ce, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── 7. GPIO interrupt ───────────────────────── */
static volatile int s_intr_count = 0;  /* DRAM — IRAM is execute-only on C5 with PMP split */

static void IRAM_ATTR gpio_isr_handler(void *arg)
{
    (void)arg;
    s_intr_count++;
}

static void test_gpio_intr(void)
{
    /* Run BEFORE test_pcnt — PCNT driver must be final owner of GPIO2/GPIO3 */
    gpio_config_t gc_out = {
        .pin_bit_mask = 1ULL << INTR_DRIVE,
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc_out);
    gpio_set_level(INTR_DRIVE, 0);

    gpio_config_t gc_in = {
        .pin_bit_mask = 1ULL << INTR_INPUT,
        .mode         = GPIO_MODE_INPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc_in);

    s_intr_count = 0;
    gpio_isr_handler_add(INTR_INPUT, gpio_isr_handler, NULL);
    gpio_set_intr_type(INTR_INPUT, GPIO_INTR_POSEDGE);
    gpio_intr_enable(INTR_INPUT);

    const int N = 20;
    for (int i = 0; i < N; i++) {
        gpio_set_level(INTR_DRIVE, 1); busy_delay_us(200);
        gpio_set_level(INTR_DRIVE, 0); busy_delay_us(200);
    }
    vTaskDelay(pdMS_TO_TICKS(20));

    gpio_intr_disable(INTR_INPUT);
    gpio_isr_handler_remove(INTR_INPUT);

    int ok = (s_intr_count == N);
    printf("AEL_INTR triggered=%d expected=%d %s\n", s_intr_count, N, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── 8. PCNT pulse count ─────────────────────── */
static void test_pcnt(void)
{
    /* Release GPIO3 from any prior config before PCNT takes ownership */
    gpio_reset_pin(PCNT_INPUT);

    gpio_config_t gc = {
        .pin_bit_mask = 1ULL << PCNT_DRIVE,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE, .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc);
    gpio_set_level(PCNT_DRIVE, 0);

    pcnt_unit_config_t ucfg = { .low_limit = -1, .high_limit = 200 };
    pcnt_unit_handle_t unit = NULL;
    pcnt_new_unit(&ucfg, &unit);

    pcnt_chan_config_t ccfg = { .edge_gpio_num = PCNT_INPUT, .level_gpio_num = -1 };
    pcnt_channel_handle_t chan = NULL;
    pcnt_new_channel(unit, &ccfg, &chan);
    pcnt_channel_set_edge_action(chan, PCNT_CHANNEL_EDGE_ACTION_INCREASE, PCNT_CHANNEL_EDGE_ACTION_HOLD);
    pcnt_channel_set_level_action(chan, PCNT_CHANNEL_LEVEL_ACTION_KEEP, PCNT_CHANNEL_LEVEL_ACTION_KEEP);

    pcnt_unit_enable(unit);
    pcnt_unit_clear_count(unit);
    pcnt_unit_start(unit);

    for (int i = 0; i < 100; i++) {
        gpio_set_level(PCNT_DRIVE, 1); busy_delay_us(10);
        gpio_set_level(PCNT_DRIVE, 0); busy_delay_us(10);
    }
    vTaskDelay(pdMS_TO_TICKS(10));

    int count = 0;
    pcnt_unit_get_count(unit, &count);
    pcnt_unit_stop(unit);
    pcnt_unit_disable(unit);
    /* do NOT call pcnt_del_* — panics on v5.5.2 with active GPIO refs */

    int ok = (count == 100);
    printf("AEL_PCNT sent=100 counted=%d %s\n", count, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── 9. UART1 loopback ───────────────────────── */
static void test_uart(void)
{
    uart_config_t cfg = {
        .baud_rate  = 115200,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .flow_ctrl  = UART_HW_FLOWCTRL_DISABLE,
    };
    uart_driver_install(UART_NUM_1, 256, 256, 0, NULL, 0);
    uart_param_config(UART_NUM_1, &cfg);
    uart_set_pin(UART_NUM_1, UART1_TX, UART1_RX,
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    const char *MSG = "AEL_UART_PING";
    const int   LEN = (int)strlen(MSG);
    uint8_t rx[32]  = {0};

    uart_flush(UART_NUM_1);
    uart_write_bytes(UART_NUM_1, MSG, LEN);
    int rxlen = uart_read_bytes(UART_NUM_1, rx, LEN, pdMS_TO_TICKS(500));
    uart_driver_delete(UART_NUM_1);

    int ok = (rxlen == LEN && memcmp(rx, MSG, LEN) == 0);
    printf("AEL_UART sent=%d recv=%d %s\n", LEN, rxlen, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── 10. ADC loopback ────────────────────────── */
static void test_adc(void)
{
    gpio_config_t gc = {
        .pin_bit_mask = 1ULL << ADC_DRIVE,
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc);

    adc_oneshot_unit_handle_t adc;
    adc_oneshot_unit_init_cfg_t unit_cfg = { .unit_id = ADC_UNIT };
    adc_oneshot_new_unit(&unit_cfg, &adc);

    adc_oneshot_chan_cfg_t chan_cfg = { .atten = ADC_ATTEN, .bitwidth = ADC_BITWIDTH_DEFAULT };
    adc_oneshot_config_channel(adc, ADC_CHAN, &chan_cfg);

    gpio_set_level(ADC_DRIVE, 1); vTaskDelay(pdMS_TO_TICKS(20));
    int raw_hi = 0; adc_oneshot_read(adc, ADC_CHAN, &raw_hi);

    gpio_set_level(ADC_DRIVE, 0); vTaskDelay(pdMS_TO_TICKS(20));
    int raw_lo = 0; adc_oneshot_read(adc, ADC_CHAN, &raw_lo);

    adc_oneshot_del_unit(adc);

    int ok = (raw_hi > ADC_HI_THRESH) && (raw_lo < ADC_LO_THRESH);
    printf("AEL_ADC raw_hi=%d raw_lo=%d %s\n", raw_hi, raw_lo, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── 11. SPI loopback ────────────────────────── */
static const uint8_t SPI_TX[] = { 0xA5, 0x5A, 0xDE, 0xAD, 0xBE, 0xEF, 0x12, 0x34 };
#define SPI_LEN ((int)sizeof(SPI_TX))

static void test_spi(void)
{
    spi_bus_config_t buscfg = {
        .mosi_io_num   = PIN_MOSI,
        .miso_io_num   = PIN_MISO,
        .sclk_io_num   = PIN_CLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
    };
    spi_bus_initialize(SPI_HOST_SEL, &buscfg, SPI_DMA_CH_AUTO);

    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 1000000,
        .mode           = 0,
        .spics_io_num   = PIN_CS,
        .queue_size     = 1,
    };
    spi_device_handle_t spi;
    spi_bus_add_device(SPI_HOST_SEL, &devcfg, &spi);

    uint8_t rx[SPI_LEN] = {0};
    spi_transaction_t t = {
        .length    = SPI_LEN * 8,
        .tx_buffer = SPI_TX,
        .rx_buffer = rx,
    };
    esp_err_t e = spi_device_transmit(spi, &t);

    spi_bus_remove_device(spi);
    spi_bus_free(SPI_HOST_SEL);

    int ok = (e == ESP_OK && memcmp(SPI_TX, rx, SPI_LEN) == 0);
    printf("AEL_SPI len=%d tx_rx_match=%d err=%d %s\n",
           SPI_LEN, ok && e == ESP_OK, (int)e, ok ? "PASS" : "FAIL");
    ok ? s_passed++ : s_failed++;
}

/* ── app_main ────────────────────────────────── */
void app_main(void)
{
    esp_log_level_set("*", ESP_LOG_WARN);

    /* Install GPIO ISR service BEFORE WiFi/BLE init so the dispatch table
     * is allocated in DRAM (heap).  If BLE installs it first, the table
     * lands in IRAM which is execute-only on C5 (PMP_IDRAM_SPLIT=y),
     * causing Store access fault in gpio_isr_handler_add(). */
    gpio_install_isr_service(0);

    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase(); nvs_flash_init();
    }
    esp_netif_init();
    esp_event_loop_create_default();

    vTaskDelay(pdMS_TO_TICKS(2000));
    printf("AEL_SUITE_FULL BOOT\n"); fflush(stdout);

    sub_hello();
    test_temperature();
    test_nvs();
    test_wifi();
    test_ble();
    test_light_sleep();
    test_pwm();
    test_gpio_intr();   /* INTR before PCNT — PCNT must be final owner of GPIO2/GPIO3 */
    test_pcnt();
    test_uart();
    test_adc();
    test_spi();

    printf("AEL_SUITE_FULL DONE passed=%d failed=%d\n", s_passed, s_failed);
    fflush(stdout);
}
