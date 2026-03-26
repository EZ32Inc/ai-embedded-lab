/* test_spi — Stage 2: SPI2 MOSI<->MISO loopback. Jumper GPIO10 <-> GPIO2. */
#include <stdio.h>
#include <string.h>
#include "ael_board_init.h"
#include "driver/spi_master.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define PIN_MOSI  GPIO_NUM_10
#define PIN_MISO  GPIO_NUM_2
#define PIN_CLK   GPIO_NUM_11
#define PIN_CS    GPIO_NUM_12

static const uint8_t SPI_TX[] = { 0xA5, 0x5A, 0xDE, 0xAD, 0xBE, 0xEF, 0x12, 0x34 };
#define SPI_LEN ((int)sizeof(SPI_TX))

void app_main(void)
{
    ael_common_init();
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

    uint8_t rx[SPI_LEN] = {0};
    spi_transaction_t t = {
        .length    = SPI_LEN * 8,
        .tx_buffer = SPI_TX,
        .rx_buffer = rx,
    };
    esp_err_t e = spi_device_transmit(spi, &t);

    spi_bus_remove_device(spi);
    spi_bus_free(SPI2_HOST);

    int ok = (e == ESP_OK && memcmp(SPI_TX, rx, SPI_LEN) == 0);
    printf("AEL_SPI len=%d match=%d err=%d %s\n",
           SPI_LEN, (e == ESP_OK && memcmp(SPI_TX, rx, SPI_LEN) == 0), (int)e,
           ok ? "PASS" : "FAIL");
    while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
}
