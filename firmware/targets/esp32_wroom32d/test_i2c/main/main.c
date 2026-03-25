/*
 * test_i2c — Stage 2: I2C master+slave loopback
 *
 * Wiring required:
 *   GPIO21 (I2C0 SDA master) ↔ GPIO13 (I2C1 SDA slave)
 *   GPIO22 (I2C0 SCL master) ↔ GPIO14 (I2C1 SCL slave)
 *
 * I2C0 master transmits 8 bytes to I2C1 slave.
 * Slave uses V1 driver (ESP32 classic has no SCL-stretch HW; V2 requires it).
 * i2c_slave_receive() is called AFTER bus_reset() to avoid premature callback.
 * Output: AEL_I2C tx_err=N rx_len=N match=N PASS|FAIL
 *
 * ESP32 classic constraints:
 *   - Two I2C controllers cannot share the same GPIO pair (GPIO matrix limitation)
 *   - V2 slave driver requires SCL stretch HW not present on ESP32 classic
 *   - Use V1 (i2c_slave_config_t, on_recv_done callback, no receive_buf_depth)
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "ael_board_init.h"
#include "driver/i2c_master.h"
#include "driver/i2c_slave.h"

#define I2C_MASTER_PORT  I2C_NUM_0
#define I2C_SLAVE_PORT   I2C_NUM_1
#define I2C_MASTER_SDA   GPIO_NUM_21
#define I2C_MASTER_SCL   GPIO_NUM_22
#define I2C_SLAVE_SDA    GPIO_NUM_13
#define I2C_SLAVE_SCL    GPIO_NUM_14
#define I2C_SLAVE_ADDR   0x5A
#define I2C_SPEED_HZ     100000
#define I2C_BUF_LEN      8

static SemaphoreHandle_t s_slv_done;
static uint8_t           s_slv_rx[I2C_BUF_LEN];
static volatile uint32_t s_slv_rx_len;

static bool i2c_slave_recv_cb(i2c_slave_dev_handle_t dev,
                               const i2c_slave_rx_done_event_data_t *evt,
                               void *arg)
{
    /* V1 driver: data is already in the buffer registered via i2c_slave_receive().
     * evt->length is not available in V1 — use the pre-known transfer size. */
    (void)dev; (void)evt; (void)arg;
    BaseType_t xw = 0;
    s_slv_rx_len = I2C_BUF_LEN;
    xSemaphoreGiveFromISR(s_slv_done, &xw);
    return (bool)xw;
}

void app_main(void)
{
    ael_common_init();

    static const uint8_t I2C_TX[I2C_BUF_LEN] = {
        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0
    };
    s_slv_done = xSemaphoreCreateBinary();
    memset(s_slv_rx, 0, sizeof(s_slv_rx));
    s_slv_rx_len = 0;

    /* Init I2C1 slave (V1 API) */
    i2c_slave_config_t slv_cfg = {
        .i2c_port       = I2C_SLAVE_PORT,
        .clk_source     = I2C_CLK_SRC_DEFAULT,
        .scl_io_num     = I2C_SLAVE_SCL,
        .sda_io_num     = I2C_SLAVE_SDA,
        .slave_addr     = I2C_SLAVE_ADDR,
        .send_buf_depth = 64,
    };
    i2c_slave_dev_handle_t slv;
    esp_err_t e = i2c_new_slave_device(&slv_cfg, &slv);
    if (e != ESP_OK) {
        vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C slave_init=0x%x FAIL\n", e);
        return;
    }

    i2c_slave_event_callbacks_t cbs = { .on_recv_done = i2c_slave_recv_cb };
    e = i2c_slave_register_event_callbacks(slv, &cbs, NULL);
    if (e != ESP_OK) {
        i2c_del_slave_device(slv);
        vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C slave_cb=0x%x FAIL\n", e);
        return;
    }

    /* Init I2C0 master */
    i2c_master_bus_config_t mcfg = {
        .i2c_port                    = I2C_MASTER_PORT,
        .sda_io_num                  = I2C_MASTER_SDA,
        .scl_io_num                  = I2C_MASTER_SCL,
        .clk_source                  = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt           = 7,
        .flags.enable_internal_pullup = true,
    };
    i2c_master_bus_handle_t bus;
    e = i2c_new_master_bus(&mcfg, &bus);
    if (e != ESP_OK) {
        i2c_del_slave_device(slv);
        vSemaphoreDelete(s_slv_done);
        printf("AEL_I2C master_init=0x%x FAIL\n", e);
        return;
    }

    i2c_device_config_t dcfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address  = I2C_SLAVE_ADDR,
        .scl_speed_hz    = I2C_SPEED_HZ,
    };
    i2c_master_dev_handle_t dev;
    i2c_master_bus_add_device(bus, &dcfg, &dev);

    vTaskDelay(pdMS_TO_TICKS(100));    /* let slave settle */
    i2c_master_bus_reset(bus);         /* 9 SCL pulses to clear any stuck state */
    vTaskDelay(pdMS_TO_TICKS(20));

    /* V1: arm receive buffer AFTER bus_reset so the 9-pulse SCL burst from
     * bus_reset does not prematurely fire on_recv_done with zeros. */
    i2c_slave_receive(slv, s_slv_rx, I2C_BUF_LEN);
    vTaskDelay(pdMS_TO_TICKS(10));     /* give slave ISR time to arm */

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
}
