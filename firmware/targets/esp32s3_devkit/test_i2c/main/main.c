/* test_i2c — Stage 2: I2C loopback using HW I2C0 master + HW I2C1 V2 slave.
 * ESP32-S3 has TWO hardware I2C controllers — no bit-bang needed!
 * Jumpers: GPIO8 <-> GPIO15 (SDA), GPIO9 <-> GPIO16 (SCL).
 *
 * Master (I2C0): SDA=GPIO8,  SCL=GPIO9
 * Slave  (I2C1): SDA=GPIO15, SCL=GPIO16
 * Requires: CONFIG_I2C_ENABLE_SLAVE_DRIVER_VERSION_2=y */
#include <stdio.h>
#include <string.h>
#include "ael_board_init.h"
#include "driver/i2c_master.h"
#include "driver/i2c_slave.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#define I2C_MASTER_PORT  ((i2c_port_num_t)0)
#define I2C_SLAVE_PORT   ((i2c_port_num_t)1)
#define I2C_MASTER_SDA   GPIO_NUM_8
#define I2C_MASTER_SCL   GPIO_NUM_9
#define I2C_SLAVE_SDA    GPIO_NUM_15
#define I2C_SLAVE_SCL    GPIO_NUM_16
#define I2C_SLAVE_ADDR   0x5A
#define I2C_BUF_LEN      8

static SemaphoreHandle_t s_slv_done;
static uint8_t           s_slv_rx[I2C_BUF_LEN];
static volatile uint32_t s_slv_rx_len;

static bool i2c_slave_recv_cb(i2c_slave_dev_handle_t slv,
                               const i2c_slave_rx_done_event_data_t *evt,
                               void *arg)
{
    (void)slv; (void)arg;
    BaseType_t xw = 0;
    uint32_t n = evt->length < I2C_BUF_LEN ? evt->length : I2C_BUF_LEN;
    memcpy(s_slv_rx, evt->buffer, n);
    s_slv_rx_len = n;
    xSemaphoreGiveFromISR(s_slv_done, &xw);
    return (bool)xw;
}

void app_main(void)
{
    ael_common_init();

    static const uint8_t I2C_TX[I2C_BUF_LEN] = {
        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0
    };
    s_slv_done   = xSemaphoreCreateBinary();
    s_slv_rx_len = 0;
    memset(s_slv_rx, 0, sizeof(s_slv_rx));

    /* Init I2C slave (V2 driver) on port 1 */
    i2c_slave_config_t slv_cfg = {
        .i2c_port          = I2C_SLAVE_PORT,
        .clk_source        = I2C_CLK_SRC_DEFAULT,
        .scl_io_num        = I2C_SLAVE_SCL,
        .sda_io_num        = I2C_SLAVE_SDA,
        .slave_addr        = I2C_SLAVE_ADDR,
        .send_buf_depth    = 100,
        .receive_buf_depth = 100,
        .flags.enable_internal_pullup = true,
    };
    i2c_slave_dev_handle_t slv;
    esp_err_t e = i2c_new_slave_device(&slv_cfg, &slv);
    if (e != ESP_OK) {
        vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C slave_init=0x%x FAIL\n", e);
        while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
    }
    i2c_slave_event_callbacks_t cbs = { .on_receive = i2c_slave_recv_cb };
    e = i2c_slave_register_event_callbacks(slv, &cbs, NULL);
    if (e != ESP_OK) {
        i2c_del_slave_device(slv); vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C slave_cb=0x%x FAIL\n", e);
        while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
    }

    /* Init I2C master bus on port 0 */
    i2c_master_bus_config_t bus_cfg = {
        .clk_source        = I2C_CLK_SRC_DEFAULT,
        .i2c_port          = I2C_MASTER_PORT,
        .scl_io_num        = I2C_MASTER_SCL,
        .sda_io_num        = I2C_MASTER_SDA,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    i2c_master_bus_handle_t bus;
    e = i2c_new_master_bus(&bus_cfg, &bus);
    if (e != ESP_OK) {
        i2c_del_slave_device(slv); vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C master_init=0x%x FAIL\n", e);
        while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
    }

    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address  = I2C_SLAVE_ADDR,
        .scl_speed_hz    = 100000,
    };
    i2c_master_dev_handle_t dev;
    e = i2c_master_bus_add_device(bus, &dev_cfg, &dev);
    if (e != ESP_OK) {
        i2c_del_master_bus(bus); i2c_del_slave_device(slv); vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C master_add_dev=0x%x FAIL\n", e);
        while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
    }

    vTaskDelay(pdMS_TO_TICKS(10));   /* let slave settle */

    /* Master transmit */
    e = i2c_master_transmit(dev, I2C_TX, I2C_BUF_LEN, 500);

    /* Wait for slave callback */
    BaseType_t got = xSemaphoreTake(s_slv_done, pdMS_TO_TICKS(500));

    i2c_master_bus_rm_device(dev);
    i2c_del_master_bus(bus);
    i2c_del_slave_device(slv);
    vSemaphoreDelete(s_slv_done);

    int match = (got == pdTRUE) && (s_slv_rx_len == I2C_BUF_LEN) &&
                (memcmp(I2C_TX, s_slv_rx, I2C_BUF_LEN) == 0);
    int ok    = (e == ESP_OK) && match;
    printf("AEL_I2C tx_err=%d rx_len=%u match=%d %s\n",
           (int)e, (unsigned)s_slv_rx_len, match, ok ? "PASS" : "FAIL");
    while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
}
