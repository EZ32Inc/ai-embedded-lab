/*
 * test_full_suite - Full board suite for ESP32-WROOM-32D (CP210X)
 *
 * Rule D "Acceptable Model": a single firmware that runs all 12 sub-tests.
 * Each sub-test is a self-contained function: independent init, independent
 * cleanup, no shared state, returns 1=PASS 0=FAIL.
 *
 * This is the CONVENIENCE LAYER.  The TRUTH LAYER is the 12 individual
 * programs in firmware/targets/esp32_wroom32d/test_XX (individual targets).
 * Those must be validated first; this suite is added afterward.
 *
 * Wiring (6 jumpers required - same as Stage 2 individual tests):
 *   GPIO25 -- GPIO26   GPIO interrupt drive / PCNT input
 *   GPIO17 -- GPIO16   UART1 TX -> RX loopback
 *   GPIO33 -> GPIO34   ADC drive -> ADC1_CH6 (input-only)
 *   GPIO23 -- GPIO19   SPI2 MOSI -- MISO
 *   GPIO21 -- GPIO13   I2C SDA: master (I2C0) -- slave (I2C1)
 *   GPIO22 -- GPIO14   I2C SCL: master (I2C0) -- slave (I2C1)
 *
 * Output tags: AEL_HELLO, AEL_NVS, AEL_WIFI, AEL_BLE, AEL_SLEEP, AEL_PWM,
 *              AEL_INTR, AEL_PCNT, AEL_UART, AEL_ADC, AEL_SPI, AEL_I2C
 *              AEL_SUITE_FULL DONE passed=N failed=M
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "ael_board_init.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "driver/uart.h"
#include "driver/spi_master.h"
#include "driver/pulse_cnt.h"
#include "driver/i2c_master.h"
#include "driver/i2c_slave.h"
#include "esp_adc/adc_oneshot.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_wifi.h"
#include "esp_sleep.h"
#include "esp_rom_sys.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/ble_gap.h"

/* -- pin assignments ---------------------------- */
#define INTR_DRIVE   GPIO_NUM_25
#define INTR_INPUT   GPIO_NUM_26
#define PCNT_DRIVE   GPIO_NUM_25
#define PCNT_INPUT   GPIO_NUM_26
#define UART1_TX     GPIO_NUM_17
#define UART1_RX     GPIO_NUM_16
#define ADC_DRIVE    GPIO_NUM_33
#define ADC_UNIT     ADC_UNIT_1
#define ADC_CHAN     ADC_CHANNEL_6
#define ADC_ATTEN    ADC_ATTEN_DB_12
#define ADC_HI_THRESH 2000
#define ADC_LO_THRESH  500
#define SPI_HOST_SEL SPI2_HOST
#define PIN_MOSI     GPIO_NUM_23
#define PIN_MISO     GPIO_NUM_19
#define PIN_CLK      GPIO_NUM_18
#define PIN_CS       GPIO_NUM_27
#define PWM_GPIO     GPIO_NUM_32
#define I2C_MASTER_PORT  I2C_NUM_0
#define I2C_SLAVE_PORT   I2C_NUM_1
#define I2C_MASTER_SDA   GPIO_NUM_21
#define I2C_MASTER_SCL   GPIO_NUM_22
#define I2C_SLAVE_SDA    GPIO_NUM_13
#define I2C_SLAVE_SCL    GPIO_NUM_14
#define I2C_SLAVE_ADDR   0x5A
#define I2C_SPEED_HZ     100000
#define I2C_BUF_LEN      8


/* -- 1. hello ----------------------------------- */
/* Implicit: if this line prints, flash+boot+console all work. */
static int sub_hello(void)
{
    printf("AEL_HELLO PASS\n");
    return 1;
}


/* -- 2. NVS ------------------------------------- */
static int sub_nvs(void)
{
    const uint32_t WVAL = 0xAE320001U;
    nvs_handle_t h;
    esp_err_t e = nvs_open("ael_fs_full", NVS_READWRITE, &h);
    if (e != ESP_OK) {
        printf("AEL_NVS open_err=0x%x FAIL\n", e);
        return 0;
    }
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


/* -- 3. WiFi ------------------------------------ */
static int sub_wifi(void)
{
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();
    wifi_scan_config_t sc = { .show_hidden = false, .scan_type = WIFI_SCAN_TYPE_PASSIVE };
    esp_wifi_scan_start(&sc, true);
    uint16_t cnt = 0;
    esp_wifi_scan_get_ap_num(&cnt);
    if (cnt > 0) {
        wifi_ap_record_t *recs = malloc(cnt * sizeof(wifi_ap_record_t));
        if (recs) { uint16_t n = cnt; esp_wifi_scan_get_ap_records(&n, recs); free(recs); }
    }
    esp_wifi_stop();
    esp_wifi_deinit();
    int ok = (cnt > 0);
    printf("AEL_WIFI ap_2g=%u %s\n", cnt, ok ? "PASS" : "FAIL");
    return ok;
}


/* -- 4. BLE ------------------------------------- */
static SemaphoreHandle_t s_ble_sem;
static volatile int      s_ble_adv;

static int _gap_cb(struct ble_gap_event *ev, void *arg)
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
    ble_gap_disc(BLE_OWN_ADDR_PUBLIC, 3000, &dp, _gap_cb, NULL);
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
    nimble_port_stop();
    vTaskDelay(pdMS_TO_TICKS(50));
    nimble_port_deinit();
    vSemaphoreDelete(s_ble_sem);
    return ok;
}


/* -- 5. Sleep ----------------------------------- */
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


/* -- 6. PWM ------------------------------------- */
static int sub_pwm(void)
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
    printf("AEL_PWM gpio=GPIO%d freq_hz=1000 duty_pct=50 %s\n", PWM_GPIO, ok ? "PASS" : "FAIL");
    /* Stop PWM cleanly before next test */
    ledc_stop(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
    return ok;
}


/* -- 7. GPIO interrupt -------------------------- */
static volatile int s_intr_count;

static void IRAM_ATTR _gpio_isr(void *arg) { (void)arg; s_intr_count++; }

static int sub_gpio_intr(void)
{
    /* Drive pin */
    gpio_config_t gc_out = {
        .pin_bit_mask = 1ULL << INTR_DRIVE, .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE, .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc_out);
    gpio_set_level(INTR_DRIVE, 0);

    /* Input pin */
    gpio_config_t gc_in = {
        .pin_bit_mask = 1ULL << INTR_INPUT, .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE, .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc_in);

    s_intr_count = 0;
    gpio_isr_handler_add(INTR_INPUT, _gpio_isr, NULL);
    gpio_set_intr_type(INTR_INPUT, GPIO_INTR_POSEDGE);
    gpio_intr_enable(INTR_INPUT);

    const int N = 20;
    for (int i = 0; i < N; i++) {
        gpio_set_level(INTR_DRIVE, 1); esp_rom_delay_us(200);
        gpio_set_level(INTR_DRIVE, 0); esp_rom_delay_us(200);
    }
    vTaskDelay(pdMS_TO_TICKS(20));

    gpio_intr_disable(INTR_INPUT);
    gpio_isr_handler_remove(INTR_INPUT);
    /* Reset drive pin low so PCNT starts clean */
    gpio_set_level(INTR_DRIVE, 0);
    gpio_reset_pin(INTR_INPUT);

    int ok = (s_intr_count == N);
    printf("AEL_INTR triggered=%d expected=%d %s\n", s_intr_count, N, ok ? "PASS" : "FAIL");
    return ok;
}


/* -- 8. PCNT ------------------------------------ */
static int sub_pcnt(void)
{
    gpio_config_t gc = {
        .pin_bit_mask = 1ULL << PCNT_DRIVE, .mode = GPIO_MODE_OUTPUT,
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
    pcnt_channel_set_edge_action(chan,
        PCNT_CHANNEL_EDGE_ACTION_INCREASE, PCNT_CHANNEL_EDGE_ACTION_HOLD);
    pcnt_channel_set_level_action(chan,
        PCNT_CHANNEL_LEVEL_ACTION_KEEP, PCNT_CHANNEL_LEVEL_ACTION_KEEP);

    pcnt_unit_enable(unit);
    pcnt_unit_clear_count(unit);
    pcnt_unit_start(unit);

    for (int i = 0; i < 100; i++) {
        gpio_set_level(PCNT_DRIVE, 1); esp_rom_delay_us(10);
        gpio_set_level(PCNT_DRIVE, 0); esp_rom_delay_us(10);
    }
    vTaskDelay(pdMS_TO_TICKS(10));

    int count = 0;
    pcnt_unit_get_count(unit, &count);
    pcnt_unit_stop(unit);
    pcnt_unit_disable(unit);
    pcnt_del_channel(chan);
    pcnt_del_unit(unit);

    int ok = (count == 100);
    printf("AEL_PCNT sent=100 counted=%d %s\n", count, ok ? "PASS" : "FAIL");
    return ok;
}


/* -- 9. UART ------------------------------------ */
static int sub_uart(void)
{
    uart_config_t cfg = {
        .baud_rate = 115200, .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE, .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    uart_driver_install(UART_NUM_1, 256, 256, 0, NULL, 0);
    uart_param_config(UART_NUM_1, &cfg);
    uart_set_pin(UART_NUM_1, UART1_TX, UART1_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    const char *MSG = "AEL_UART_PING";
    const int   LEN = (int)strlen(MSG);
    uint8_t rx[32] = {0};
    uart_flush(UART_NUM_1);
    uart_write_bytes(UART_NUM_1, MSG, LEN);
    int rxlen = uart_read_bytes(UART_NUM_1, rx, LEN, pdMS_TO_TICKS(500));
    uart_driver_delete(UART_NUM_1);

    int ok = (rxlen == LEN && memcmp(rx, MSG, LEN) == 0);
    printf("AEL_UART sent=%d recv=%d %s\n", LEN, rxlen, ok ? "PASS" : "FAIL");
    return ok;
}


/* -- 10. ADC ------------------------------------ */
static int sub_adc(void)
{
    gpio_config_t gc = {
        .pin_bit_mask = 1ULL << ADC_DRIVE, .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE, .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
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
    return ok;
}


/* -- 11. SPI ------------------------------------ */
static const uint8_t SPI_TX[] = { 0xA5, 0x5A, 0xDE, 0xAD, 0xBE, 0xEF, 0x12, 0x34 };
#define SPI_LEN ((int)sizeof(SPI_TX))

static int sub_spi(void)
{
    spi_bus_config_t buscfg = {
        .mosi_io_num = PIN_MOSI, .miso_io_num = PIN_MISO, .sclk_io_num = PIN_CLK,
        .quadwp_io_num = -1, .quadhd_io_num = -1,
    };
    spi_bus_initialize(SPI_HOST_SEL, &buscfg, SPI_DMA_CH_AUTO);
    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 1000000, .mode = 0, .spics_io_num = PIN_CS, .queue_size = 1,
    };
    spi_device_handle_t spi;
    spi_bus_add_device(SPI_HOST_SEL, &devcfg, &spi);

    uint8_t rx[SPI_LEN] = {0};
    spi_transaction_t t = { .length = SPI_LEN * 8, .tx_buffer = SPI_TX, .rx_buffer = rx };
    esp_err_t e = spi_device_transmit(spi, &t);

    spi_bus_remove_device(spi);
    spi_bus_free(SPI_HOST_SEL);

    int match = (memcmp(SPI_TX, rx, SPI_LEN) == 0);
    int ok = (e == ESP_OK && match);
    printf("AEL_SPI len=%d match=%d err=%d %s\n", SPI_LEN, match, (int)e, ok ? "PASS" : "FAIL");
    return ok;
}


/* -- 12. I2C ------------------------------------ */
static SemaphoreHandle_t s_slv_done;
static uint8_t           s_slv_rx[I2C_BUF_LEN];
static volatile uint32_t s_slv_rx_len;

static bool _i2c_recv_cb(i2c_slave_dev_handle_t dev,
                          const i2c_slave_rx_done_event_data_t *evt,
                          void *arg)
{
    (void)dev; (void)evt; (void)arg;
    BaseType_t xw = 0;
    s_slv_rx_len = I2C_BUF_LEN;
    xSemaphoreGiveFromISR(s_slv_done, &xw);
    return (bool)xw;
}

static int sub_i2c(void)
{
    static const uint8_t I2C_TX[I2C_BUF_LEN] = {
        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0
    };
    s_slv_done = xSemaphoreCreateBinary();
    memset(s_slv_rx, 0, sizeof(s_slv_rx));
    s_slv_rx_len = 0;

    i2c_slave_config_t slv_cfg = {
        .i2c_port = I2C_SLAVE_PORT, .clk_source = I2C_CLK_SRC_DEFAULT,
        .scl_io_num = I2C_SLAVE_SCL, .sda_io_num = I2C_SLAVE_SDA,
        .slave_addr = I2C_SLAVE_ADDR, .send_buf_depth = 64,
    };
    i2c_slave_dev_handle_t slv;
    esp_err_t e = i2c_new_slave_device(&slv_cfg, &slv);
    if (e != ESP_OK) {
        vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C slave_init=0x%x FAIL\n", e);
        return 0;
    }
    i2c_slave_event_callbacks_t cbs = { .on_recv_done = _i2c_recv_cb };
    e = i2c_slave_register_event_callbacks(slv, &cbs, NULL);
    if (e != ESP_OK) {
        i2c_del_slave_device(slv); vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C slave_cb=0x%x FAIL\n", e);
        return 0;
    }

    i2c_master_bus_config_t mcfg = {
        .i2c_port = I2C_MASTER_PORT, .sda_io_num = I2C_MASTER_SDA,
        .scl_io_num = I2C_MASTER_SCL, .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7, .flags.enable_internal_pullup = true,
    };
    i2c_master_bus_handle_t bus;
    e = i2c_new_master_bus(&mcfg, &bus);
    if (e != ESP_OK) {
        i2c_del_slave_device(slv); vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C master_init=0x%x FAIL\n", e);
        return 0;
    }

    i2c_device_config_t dcfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = I2C_SLAVE_ADDR, .scl_speed_hz = I2C_SPEED_HZ,
    };
    i2c_master_dev_handle_t dev;
    i2c_master_bus_add_device(bus, &dcfg, &dev);

    vTaskDelay(pdMS_TO_TICKS(100));
    i2c_master_bus_reset(bus);
    vTaskDelay(pdMS_TO_TICKS(20));
    i2c_slave_receive(slv, s_slv_rx, I2C_BUF_LEN);
    vTaskDelay(pdMS_TO_TICKS(10));

    esp_err_t we = i2c_master_transmit(dev, I2C_TX, I2C_BUF_LEN, 500);
    BaseType_t got = xSemaphoreTake(s_slv_done, pdMS_TO_TICKS(500));

    i2c_master_bus_rm_device(dev);
    i2c_del_master_bus(bus);
    i2c_del_slave_device(slv);
    vSemaphoreDelete(s_slv_done);

    int match = (got == pdTRUE) &&
                ((uint32_t)s_slv_rx_len == I2C_BUF_LEN) &&
                (memcmp(I2C_TX, s_slv_rx, I2C_BUF_LEN) == 0);
    int ok = (we == ESP_OK) && match;
    printf("AEL_I2C tx_err=%d rx_len=%u match=%d %s\n",
           (int)we, (unsigned)s_slv_rx_len, match, ok ? "PASS" : "FAIL");
    return ok;
}


/* -- app_main ----------------------------------- */
void app_main(void)
{
    /* Shared init - order matters:
     *   1. ael_common_init   : NVS flash + log suppression
     *   2. ael_gpio_isr_init : must be before WiFi/BLE (known ESP32 pitfall)
     *   3. ael_netif_init    : TCP/IP stack + event loop for WiFi sub-test  */
    ael_common_init();
    ael_gpio_isr_init();
    ael_netif_init();

    vTaskDelay(pdMS_TO_TICKS(500));
    printf("AEL_SUITE_FULL BOOT\n"); fflush(stdout);

    int passed = 0;
    const int TOTAL = 12;

    passed += sub_hello();         /*  1 - console    (Stage 0) */
    passed += sub_nvs();           /*  2 - NVS        (Stage 1) */
    passed += sub_wifi();          /*  3 - WiFi       (Stage 1) */
    passed += sub_ble();           /*  4 - BLE        (Stage 1) */
    passed += sub_sleep();         /*  5 - sleep      (Stage 1) */
    passed += sub_pwm();           /*  6 - PWM        (Stage 1) */
    passed += sub_gpio_intr();     /*  7 - GPIO intr  (Stage 2) - before PCNT */
    passed += sub_pcnt();          /*  8 - PCNT       (Stage 2) */
    passed += sub_uart();          /*  9 - UART1      (Stage 2) */
    passed += sub_adc();           /* 10 - ADC        (Stage 2) */
    passed += sub_spi();           /* 11 - SPI        (Stage 2) */
    passed += sub_i2c();           /* 12 - I2C        (Stage 2) */

    printf("AEL_SUITE_FULL DONE passed=%d failed=%d\n", passed, TOTAL - passed);
    fflush(stdout);
}
