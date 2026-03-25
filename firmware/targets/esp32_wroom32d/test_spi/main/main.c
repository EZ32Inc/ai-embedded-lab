/*
 * test_spi — Stage 2: SPI2 MOSI↔MISO loopback
 *
 * Wiring required: GPIO23 (MOSI) ↔ GPIO19 (MISO)
 *   CLK  = GPIO18 (no external connection needed)
 *   CS   = GPIO27 (no external connection needed)
 *
 * Transmits 8 bytes and verifies the received data matches via MOSI→MISO wire.
 * Output: AEL_SPI len=8 match=1 err=0 PASS|FAIL
 */

#include <stdio.h>
#include <string.h>
#include "ael_board_init.h"
#include "driver/spi_master.h"

#define SPI_HOST_SEL SPI2_HOST
#define PIN_MOSI     GPIO_NUM_23
#define PIN_MISO     GPIO_NUM_19
#define PIN_CLK      GPIO_NUM_18
#define PIN_CS       GPIO_NUM_27

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

    int match = (memcmp(SPI_TX, rx, SPI_LEN) == 0);
    int ok    = (e == ESP_OK && match);
    printf("AEL_SPI len=%d match=%d err=%d %s\n", SPI_LEN, match, (int)e, ok ? "PASS" : "FAIL");
}
