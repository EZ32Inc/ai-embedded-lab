/* test_full_suite - Full board suite for ESP32-C6 DevKit (dual USB).
 *
 * Rule D "Acceptable Model": single firmware running all 13 sub-tests.
 * Each sub-test is self-contained: independent init, cleanup, returns 1=PASS 0=FAIL.
 * This is the CONVENIENCE LAYER. The TRUTH LAYER is the 13 individual programs
 * in firmware/targets/esp32c6_devkit/test_XX (individual targets).
 * Those must be validated first; this suite is added afterward.
 *
 * Wiring (6 jumpers required - same as Stage 2 individual tests):
 *   GPIO20 -- GPIO21   GPIO interrupt drive / PCNT input (shared)
 *   GPIO18 -- GPIO19   UART1 TX -> RX loopback
 *   GPIO22 -> GPIO4    ADC drive -> ADC1_CH4 (input-only)
 *   GPIO10 -- GPIO2    SPI2 MOSI -- MISO loopback
 *   GPIO8  -- GPIO6    I2C SDA: slave (I2C0) -- bit-bang master
 *   GPIO9  -- GPIO7    I2C SCL: slave (I2C0) -- bit-bang master
 *
 * Output tags: AEL_HELLO, AEL_NVS, AEL_TEMP, AEL_WIFI, AEL_BLE, AEL_SLEEP,
 *              AEL_PWM, AEL_INTR, AEL_PCNT, AEL_UART, AEL_ADC, AEL_SPI, AEL_I2C
 *              AEL_SUITE_FULL DONE passed=N failed=M
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
#include "driver/uart.h"
#include "driver/spi_master.h"
#include "driver/i2c_slave.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_sleep.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "host/ble_gap.h"
#include "host/ble_hs.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "nvs.h"
#include "ael_board_init.h"

/* ------------------------------------------------------------------ */
/* Shared helpers                                                       */
/* ------------------------------------------------------------------ */

static void busy_delay_us(uint32_t us)
{
    int64_t end = esp_timer_get_time() + (int64_t)us;
    while (esp_timer_get_time() < end) {}
}

/* ------------------------------------------------------------------ */
/* Pin assignments                                                      */
/* ------------------------------------------------------------------ */

#define INTR_DRIVE  GPIO_NUM_20
#define INTR_INPUT  GPIO_NUM_21
#define PCNT_DRIVE  GPIO_NUM_20
#define PCNT_INPUT  GPIO_NUM_21
#define UART1_TX    GPIO_NUM_18
#define UART1_RX    GPIO_NUM_19
#define ADC_DRIVE   GPIO_NUM_22
#define ADC_UNIT    ADC_UNIT_1
#define ADC_CHAN    ADC_CHANNEL_4
#define ADC_ATTEN   ADC_ATTEN_DB_12
#define PWM_GPIO    GPIO_NUM_3
#define PIN_MOSI    GPIO_NUM_10
#define PIN_MISO    GPIO_NUM_2
#define PIN_CLK     GPIO_NUM_11
#define PIN_CS      GPIO_NUM_12
#define I2C_SLV_SDA GPIO_NUM_8
#define I2C_SLV_SCL GPIO_NUM_9
#define BB_SDA      GPIO_NUM_6
#define BB_SCL      GPIO_NUM_7
#define BS_ADDR     0x5A
#define I2C_BUF_LEN 8
#define BB_HALF_US  50

/* ------------------------------------------------------------------ */
/* 1. Hello                                                             */
/* ------------------------------------------------------------------ */
static int sub_hello(void)
{
    printf("AEL_HELLO board=ESP32C6 PASS\n");
    return 1;
}

/* ------------------------------------------------------------------ */
/* 2. NVS                                                               */
/* ------------------------------------------------------------------ */
static int sub_nvs(void)
{
    const uint32_t WVAL = 0xAE1C00FFU;
    nvs_handle_t h;
    esp_err_t e = nvs_open("ael_fs_full", NVS_READWRITE, &h);
    if (e != ESP_OK) { printf("AEL_NVS open_err=0x%x FAIL\n", e); return 0; }
    nvs_set_u32(h, "ael_val", WVAL);
    nvs_commit(h);
    uint32_t rval = 0;
    e = nvs_get_u32(h, "ael_val", &rval);
    nvs_close(h);
    int ok = (e == ESP_OK && rval == WVAL);
    printf("AEL_NVS wrote=0x%08lX read=0x%08lX %s\n",
           (unsigned long)WVAL, (unsigned long)rval, ok ? "PASS" : "FAIL");
    return ok;
}

/* ------------------------------------------------------------------ */
/* 3. Temperature sensor                                                */
/* ------------------------------------------------------------------ */
static int sub_temp(void)
{
    temperature_sensor_handle_t sensor = NULL;
    temperature_sensor_config_t cfg = TEMPERATURE_SENSOR_CONFIG_DEFAULT(10, 80);
    esp_err_t e = temperature_sensor_install(&cfg, &sensor);
    if (e != ESP_OK) { printf("AEL_TEMP install_err=0x%x FAIL\n", e); return 0; }
    temperature_sensor_enable(sensor);
    float celsius = 0.0f;
    temperature_sensor_get_celsius(sensor, &celsius);
    temperature_sensor_disable(sensor);
    temperature_sensor_uninstall(sensor);
    int ok = (celsius > 5.0f && celsius < 90.0f);
    printf("AEL_TEMP celsius=%.1f %s\n", celsius, ok ? "PASS" : "FAIL");
    return ok;
}

/* ------------------------------------------------------------------ */
/* 4. Wi-Fi                                                             */
/* ------------------------------------------------------------------ */
static int sub_wifi(void)
{
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t wcfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&wcfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();
    wifi_scan_config_t scfg = { .scan_type = WIFI_SCAN_TYPE_PASSIVE };
    esp_wifi_scan_start(&scfg, true);
    uint16_t ap_count = 0;
    esp_wifi_scan_get_ap_num(&ap_count);
    esp_wifi_stop();
    esp_wifi_deinit();
    int ok = (ap_count >= 1);
    printf("AEL_WIFI ap_count=%u %s\n", (unsigned)ap_count, ok ? "PASS" : "FAIL");
    return ok;
}

/* ------------------------------------------------------------------ */
/* 5. BLE                                                               */
/* ------------------------------------------------------------------ */
static SemaphoreHandle_t s_ble_sem;
static volatile int      s_ble_adv = 0;

static int _ble_gap_cb(struct ble_gap_event *ev, void *arg)
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
    ble_gap_disc(BLE_OWN_ADDR_PUBLIC, 3000, &dp, _ble_gap_cb, NULL);
}
static void _ble_host_task(void *p) { (void)p; nimble_port_run(); nimble_port_freertos_deinit(); }

static int sub_ble(void)
{
    s_ble_sem = xSemaphoreCreateBinary();
    s_ble_adv = 0;
    nimble_port_init();
    ble_hs_cfg.sync_cb = _ble_sync_cb;
    nimble_port_freertos_init(_ble_host_task);
    xSemaphoreTake(s_ble_sem, pdMS_TO_TICKS(5000));
    int ok = (s_ble_adv > 0);
    printf("AEL_BLE advertisers=%d %s\n", s_ble_adv, ok ? "PASS" : "FAIL");
    /* Stop NimBLE before I2C bit-bang -- high-priority host task causes
     * timing jitter that prevents the bit-bang slave from detecting START. */
    nimble_port_stop();
    vTaskDelay(pdMS_TO_TICKS(50));
    nimble_port_deinit();
    vSemaphoreDelete(s_ble_sem);
    return ok;
}

/* ------------------------------------------------------------------ */
/* 6. Light sleep                                                       */
/* ------------------------------------------------------------------ */
static int sub_sleep(void)
{
    printf("AEL_SLEEP entering\n"); fflush(stdout);
    esp_sleep_enable_timer_wakeup(1000000ULL);
    esp_light_sleep_start();
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    int ok = (cause == ESP_SLEEP_WAKEUP_TIMER);
    printf("AEL_SLEEP wakeup_cause=%d %s\n", (int)cause, ok ? "PASS" : "FAIL");
    return ok;
}

/* ------------------------------------------------------------------ */
/* 7. PWM                                                               */
/* ------------------------------------------------------------------ */
static int sub_pwm(void)
{
    ledc_timer_config_t tc = {
        .speed_mode      = LEDC_LOW_SPEED_MODE,
        .timer_num       = LEDC_TIMER_0,
        .duty_resolution = LEDC_TIMER_10_BIT,
        .freq_hz         = 1000,
        .clk_cfg         = LEDC_AUTO_CLK,
    };
    esp_err_t te = ledc_timer_config(&tc);
    ledc_channel_config_t cc = {
        .gpio_num   = PWM_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel    = LEDC_CHANNEL_0,
        .timer_sel  = LEDC_TIMER_0,
        .duty       = 512,
        .hpoint     = 0,
    };
    esp_err_t ce = ledc_channel_config(&cc);
    int ok = (te == ESP_OK && ce == ESP_OK);
    printf("AEL_PWM gpio=GPIO%d freq_hz=1000 duty_pct=50 %s\n", PWM_GPIO, ok ? "PASS" : "FAIL");
    ledc_stop(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
    return ok;
}

/* ------------------------------------------------------------------ */
/* 8. GPIO interrupt                                                    */
/* ------------------------------------------------------------------ */
static volatile int s_intr_count = 0;

static void IRAM_ATTR gpio_isr_handler(void *arg)
{
    (void)arg;
    s_intr_count++;
}

static int sub_gpio_intr(void)
{
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
    /* Release INTR_INPUT so PCNT can take ownership of GPIO21 */
    gpio_set_level(INTR_DRIVE, 0);
    gpio_reset_pin(INTR_INPUT);

    int ok = (s_intr_count == N);
    printf("AEL_INTR triggered=%d expected=%d %s\n", s_intr_count, N, ok ? "PASS" : "FAIL");
    return ok;
}

/* ------------------------------------------------------------------ */
/* 9. PCNT                                                              */
/* ------------------------------------------------------------------ */
static int sub_pcnt(void)
{
    gpio_config_t gc = {
        .pin_bit_mask = 1ULL << PCNT_DRIVE,
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc);
    gpio_set_level(PCNT_DRIVE, 0);

    pcnt_unit_config_t ucfg = { .low_limit = -1, .high_limit = 200 };
    pcnt_unit_handle_t unit = NULL;
    pcnt_new_unit(&ucfg, &unit);

    pcnt_chan_config_t ccfg = { .edge_gpio_num = PCNT_INPUT, .level_gpio_num = -1 };
    pcnt_channel_handle_t chan = NULL;
    pcnt_new_channel(unit, &ccfg, &chan);
    pcnt_channel_set_edge_action(chan,
        PCNT_CHANNEL_EDGE_ACTION_INCREASE, PCNT_CHANNEL_EDGE_ACTION_HOLD);
    pcnt_channel_set_level_action(chan,
        PCNT_CHANNEL_LEVEL_ACTION_KEEP, PCNT_CHANNEL_LEVEL_ACTION_KEEP);

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

    int ok = (count == 100);
    printf("AEL_PCNT sent=100 counted=%d %s\n", count, ok ? "PASS" : "FAIL");
    return ok;
}

/* ------------------------------------------------------------------ */
/* 10. UART                                                             */
/* ------------------------------------------------------------------ */
static int sub_uart(void)
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
    uint8_t     rx[32] = {0};

    uart_flush(UART_NUM_1);
    uart_write_bytes(UART_NUM_1, MSG, LEN);
    int rxlen = uart_read_bytes(UART_NUM_1, rx, LEN, pdMS_TO_TICKS(500));
    uart_driver_delete(UART_NUM_1);

    int ok = (rxlen == LEN && memcmp(rx, MSG, LEN) == 0);
    printf("AEL_UART sent=%d recv=%d %s\n", LEN, rxlen, ok ? "PASS" : "FAIL");
    return ok;
}

/* ------------------------------------------------------------------ */
/* 11. ADC                                                              */
/* ------------------------------------------------------------------ */
static int sub_adc(void)
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
    adc_oneshot_unit_init_cfg_t ucfg = { .unit_id = ADC_UNIT };
    adc_oneshot_new_unit(&ucfg, &adc);

    adc_oneshot_chan_cfg_t ccfg = { .atten = ADC_ATTEN, .bitwidth = ADC_BITWIDTH_DEFAULT };
    adc_oneshot_config_channel(adc, ADC_CHAN, &ccfg);

    gpio_set_level(ADC_DRIVE, 1); vTaskDelay(pdMS_TO_TICKS(20));
    int raw_hi = 0; adc_oneshot_read(adc, ADC_CHAN, &raw_hi);

    gpio_set_level(ADC_DRIVE, 0); vTaskDelay(pdMS_TO_TICKS(20));
    int raw_lo = 0; adc_oneshot_read(adc, ADC_CHAN, &raw_lo);

    adc_oneshot_del_unit(adc);

    int ok = (raw_hi > 2000) && (raw_lo < 500);
    printf("AEL_ADC raw_hi=%d raw_lo=%d %s\n", raw_hi, raw_lo, ok ? "PASS" : "FAIL");
    return ok;
}

/* ------------------------------------------------------------------ */
/* 12. SPI                                                              */
/* ------------------------------------------------------------------ */
static int sub_spi(void)
{
    static const uint8_t TX[] = { 0xA5, 0x5A, 0xDE, 0xAD, 0xBE, 0xEF, 0x12, 0x34 };
    const int LEN = (int)sizeof(TX);

    spi_bus_config_t buscfg = {
        .mosi_io_num   = PIN_MOSI,
        .miso_io_num   = PIN_MISO,
        .sclk_io_num   = PIN_CLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
    };
    spi_bus_initialize(SPI2_HOST, &buscfg, SPI_DMA_CH_AUTO);

    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 1000000,
        .mode           = 0,
        .spics_io_num   = PIN_CS,
        .queue_size     = 1,
    };
    spi_device_handle_t spi;
    spi_bus_add_device(SPI2_HOST, &devcfg, &spi);

    uint8_t rx[8] = {0};
    spi_transaction_t t = { .length = LEN * 8, .tx_buffer = TX, .rx_buffer = rx };
    esp_err_t e = spi_device_transmit(spi, &t);

    spi_bus_remove_device(spi);
    spi_bus_free(SPI2_HOST);

    int ok = (e == ESP_OK && memcmp(TX, rx, LEN) == 0);
    printf("AEL_SPI len=%d match=%d err=%d %s\n",
           LEN, (e == ESP_OK && memcmp(TX, rx, LEN) == 0), (int)e, ok ? "PASS" : "FAIL");
    return ok;
}

/* ------------------------------------------------------------------ */
/* 13. I2C (V2 slave + bit-bang master)                                 */
/* ------------------------------------------------------------------ */
static void bb_delay(void) { busy_delay_us(BB_HALF_US); }
static void bb_wait_scl_hi(void)
{
    int64_t t = esp_timer_get_time() + 10000LL;
    while (!gpio_get_level(BB_SCL) && esp_timer_get_time() < t) {}
}
static void bb_init(void)
{
    gpio_set_level(BB_SDA, 1); gpio_set_level(BB_SCL, 1);
    gpio_config_t gc = {
        .pin_bit_mask = (1ULL << BB_SDA) | (1ULL << BB_SCL),
        .mode         = GPIO_MODE_INPUT_OUTPUT_OD,
        .pull_up_en   = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc); bb_delay();
}
static void bb_start(void)
{
    gpio_set_level(BB_SDA,1);bb_delay();
    gpio_set_level(BB_SCL,1);bb_delay();
    gpio_set_level(BB_SDA,0);bb_delay();
    gpio_set_level(BB_SCL,0);bb_delay();
}
static void bb_stop(void)
{
    gpio_set_level(BB_SDA,0);bb_delay();
    gpio_set_level(BB_SCL,1);bb_wait_scl_hi();bb_delay();
    gpio_set_level(BB_SDA,1);bb_delay();
}
static int bb_write_byte(uint8_t byte)
{
    for (int b=7;b>=0;b--) {
        gpio_set_level(BB_SDA,(byte>>b)&1);bb_delay();
        gpio_set_level(BB_SCL,1);bb_wait_scl_hi();bb_delay();
        gpio_set_level(BB_SCL,0);bb_delay();
    }
    gpio_set_level(BB_SDA,1);bb_delay();
    gpio_set_level(BB_SCL,1);bb_wait_scl_hi();bb_delay();
    int ack=!gpio_get_level(BB_SDA);
    gpio_set_level(BB_SCL,0);bb_delay();
    return ack;
}
static int bb_transmit(uint8_t addr, const uint8_t *data, int len)
{
    bb_start();
    if (!bb_write_byte((uint8_t)((addr<<1)|0))) { bb_stop(); return -1; }
    for (int i=0;i<len;i++) { if (!bb_write_byte(data[i])) { bb_stop(); return -(i+2); } }
    bb_stop(); return 0;
}

static SemaphoreHandle_t s_slv_done;
static uint8_t           s_slv_rx[I2C_BUF_LEN];
static volatile uint32_t s_slv_rx_len;

static bool i2c_slv_recv_cb(i2c_slave_dev_handle_t dev,
                             const i2c_slave_rx_done_event_data_t *evt, void *arg)
{
    (void)dev; (void)arg;
    BaseType_t xw = 0;
    uint32_t n = evt->length < I2C_BUF_LEN ? evt->length : I2C_BUF_LEN;
    memcpy(s_slv_rx, evt->buffer, n);
    s_slv_rx_len = n;
    xSemaphoreGiveFromISR(s_slv_done, &xw);
    return (bool)xw;
}

static int sub_i2c(void)
{
    static const uint8_t TX[I2C_BUF_LEN] = { 0x12,0x34,0x56,0x78,0x9A,0xBC,0xDE,0xF0 };
    s_slv_done = xSemaphoreCreateBinary();
    memset(s_slv_rx, 0, sizeof(s_slv_rx));
    s_slv_rx_len = 0;

    i2c_slave_config_t slv_cfg = {
        .i2c_port          = (i2c_port_num_t)0,
        .clk_source        = I2C_CLK_SRC_DEFAULT,
        .scl_io_num        = I2C_SLV_SCL,
        .sda_io_num        = I2C_SLV_SDA,
        .slave_addr        = BS_ADDR,
        .send_buf_depth    = 100,
        .receive_buf_depth = 100,
        .flags.enable_internal_pullup = true,
    };
    i2c_slave_dev_handle_t slv;
    esp_err_t e = i2c_new_slave_device(&slv_cfg, &slv);
    if (e != ESP_OK) {
        vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C slave_init=0x%x FAIL\n", e); return 0;
    }
    i2c_slave_event_callbacks_t cbs = { .on_receive = i2c_slv_recv_cb };
    e = i2c_slave_register_event_callbacks(slv, &cbs, NULL);
    if (e != ESP_OK) {
        i2c_del_slave_device(slv); vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C slave_cb=0x%x FAIL\n", e); return 0;
    }
    bb_init();
    vTaskDelay(pdMS_TO_TICKS(10));
    int tx_err = bb_transmit(BS_ADDR, TX, I2C_BUF_LEN);
    BaseType_t got = xSemaphoreTake(s_slv_done, pdMS_TO_TICKS(500));
    i2c_del_slave_device(slv);
    vSemaphoreDelete(s_slv_done);

    int match = (got==pdTRUE) && (s_slv_rx_len==I2C_BUF_LEN) &&
                (memcmp(TX, s_slv_rx, I2C_BUF_LEN)==0);
    int ok = (tx_err==0) && match;
    printf("AEL_I2C tx_err=%d rx_len=%u match=%d %s\n",
           tx_err, (unsigned)s_slv_rx_len, match, ok ? "PASS" : "FAIL");
    return ok;
}

/* ------------------------------------------------------------------ */
/* app_main                                                             */
/* ------------------------------------------------------------------ */
void app_main(void)
{
    ael_common_init();
    ael_gpio_isr_init();   /* must be before ael_netif_init */
    ael_netif_init();

    int passed = 0;
    const int TOTAL = 13;

    passed += sub_hello();
    passed += sub_nvs();
    passed += sub_temp();
    passed += sub_wifi();
    passed += sub_ble();   /* stops NimBLE before I2C bit-bang */
    passed += sub_sleep();
    passed += sub_pwm();
    passed += sub_gpio_intr();  /* must run before sub_pcnt -- shared GPIO20/21 */
    passed += sub_pcnt();
    passed += sub_uart();
    passed += sub_adc();
    passed += sub_spi();
    passed += sub_i2c();

    printf("AEL_SUITE_FULL DONE passed=%d failed=%d\n", passed, TOTAL - passed);
    fflush(stdout);
    while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
}
