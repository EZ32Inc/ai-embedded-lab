#include <stdio.h>
#include <string.h>
#include "esp_log.h"
#include "driver/gpio.h"
#include "driver/i2c_slave.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "nvs_flash.h"

/* Bit-bang master: SDA=GPIO8, SCL=GPIO13
 * HW I2C V2 slave: SDA=GPIO14, SCL=GPIO23
 * Jumpers: GPIO8 <-> GPIO14 (SDA),  GPIO13 <-> GPIO23 (SCL)
 * BB_HALF_US=50 -> ~10kHz (CE 958116e1: conservative for ADDRESS_MATCH stretch) */
#define I2C_SLAVE_PORT   ((i2c_port_num_t)0)
#define I2C_SLAVE_SDA    GPIO_NUM_14
#define I2C_SLAVE_SCL    GPIO_NUM_23
#define BB_SDA           GPIO_NUM_8
#define BB_SCL           GPIO_NUM_13
#define BS_ADDR          0x5A
#define I2C_BUF_LEN      8
#define BB_HALF_US       50

static void busy_delay_us(uint32_t us)
{
    int64_t end = esp_timer_get_time() + (int64_t)us;
    while (esp_timer_get_time() < end) {}
}

static void bb_delay(void) { busy_delay_us(BB_HALF_US); }

static void bb_wait_scl_hi(void)
{
    int64_t t = esp_timer_get_time() + 10000LL;
    while (!gpio_get_level(BB_SCL) && esp_timer_get_time() < t) {}
}

static void bb_init(void)
{
    gpio_set_level(BB_SDA, 1);
    gpio_set_level(BB_SCL, 1);
    gpio_config_t gc = {
        .pin_bit_mask = (1ULL << BB_SDA) | (1ULL << BB_SCL),
        .mode = GPIO_MODE_INPUT_OUTPUT_OD,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&gc);
    bb_delay();
}

static void bb_start(void)
{
    gpio_set_level(BB_SDA, 1); bb_delay();
    gpio_set_level(BB_SCL, 1); bb_delay();
    gpio_set_level(BB_SDA, 0); bb_delay();
    gpio_set_level(BB_SCL, 0); bb_delay();
}

static void bb_stop(void)
{
    gpio_set_level(BB_SDA, 0); bb_delay();
    gpio_set_level(BB_SCL, 1); bb_wait_scl_hi(); bb_delay();
    gpio_set_level(BB_SDA, 1); bb_delay();
}

static int bb_write_byte(uint8_t byte)
{
    for (int b = 7; b >= 0; b--) {
        gpio_set_level(BB_SDA, (byte >> b) & 1); bb_delay();
        gpio_set_level(BB_SCL, 1); bb_wait_scl_hi(); bb_delay();
        gpio_set_level(BB_SCL, 0); bb_delay();
    }
    gpio_set_level(BB_SDA, 1); bb_delay();
    gpio_set_level(BB_SCL, 1); bb_wait_scl_hi(); bb_delay();
    int ack = !gpio_get_level(BB_SDA);
    gpio_set_level(BB_SCL, 0); bb_delay();
    return ack;
}

static int bb_transmit(uint8_t addr, const uint8_t *data, int len)
{
    bb_start();
    if (!bb_write_byte((uint8_t)((addr << 1) | 0))) { bb_stop(); return -1; }
    for (int i = 0; i < len; i++) {
        if (!bb_write_byte(data[i])) { bb_stop(); return -(i + 2); }
    }
    bb_stop();
    return 0;
}

static SemaphoreHandle_t s_slv_done;
static uint8_t           s_slv_rx[I2C_BUF_LEN];
static volatile uint32_t s_slv_rx_len;

static bool i2c_slave_recv_cb(i2c_slave_dev_handle_t i2c_slave,
                               const i2c_slave_rx_done_event_data_t *evt_data,
                               void *arg)
{
    (void)i2c_slave; (void)arg;
    BaseType_t xw = 0;
    uint32_t n = evt_data->length < I2C_BUF_LEN ? evt_data->length : I2C_BUF_LEN;
    memcpy(s_slv_rx, evt_data->buffer, n);
    s_slv_rx_len = n;
    xSemaphoreGiveFromISR(s_slv_done, &xw);
    return (bool)xw;
}

void app_main(void)
{
    esp_log_level_set("*", ESP_LOG_WARN);
    gpio_install_isr_service(0);
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase(); nvs_flash_init();
    }

    static const uint8_t I2C_TX[I2C_BUF_LEN] = { 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0 };
    s_slv_done = xSemaphoreCreateBinary();
    memset(s_slv_rx, 0, sizeof(s_slv_rx));
    s_slv_rx_len = 0;

    i2c_slave_config_t slv_cfg = {
        .i2c_port = I2C_SLAVE_PORT,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .scl_io_num = I2C_SLAVE_SCL,
        .sda_io_num = I2C_SLAVE_SDA,
        .slave_addr = BS_ADDR,
        .send_buf_depth    = 100,
        .receive_buf_depth = 100,
        .flags.enable_internal_pullup = true,
    };
    i2c_slave_dev_handle_t slv;
    esp_err_t e = i2c_new_slave_device(&slv_cfg, &slv);
    if (e != ESP_OK) {
        vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C slave_init=0x%x FAIL\n", e);
        fflush(stdout);
        return;
    }

    i2c_slave_event_callbacks_t cbs = { .on_receive = i2c_slave_recv_cb };
    e = i2c_slave_register_event_callbacks(slv, &cbs, NULL);
    if (e != ESP_OK) {
        i2c_del_slave_device(slv); vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C slave_cb=0x%x FAIL\n", e);
        fflush(stdout);
        return;
    }

    bb_init();
    vTaskDelay(pdMS_TO_TICKS(10));

    int tx_err = bb_transmit(BS_ADDR, I2C_TX, I2C_BUF_LEN);
    BaseType_t got = xSemaphoreTake(s_slv_done, pdMS_TO_TICKS(500));

    i2c_del_slave_device(slv);
    vSemaphoreDelete(s_slv_done);

    int match = (got == pdTRUE) && (s_slv_rx_len == I2C_BUF_LEN) &&
                (memcmp(I2C_TX, s_slv_rx, I2C_BUF_LEN) == 0);
    int ok = (tx_err == 0) && match;
    printf("AEL_I2C tx_err=%d rx_len=%u match=%d %s\n",
           tx_err, (unsigned)s_slv_rx_len, match, ok ? "PASS" : "FAIL");
    fflush(stdout);
}
