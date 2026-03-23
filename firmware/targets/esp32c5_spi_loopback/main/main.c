/*
 * esp32c5_spi_loopback
 *
 * SPI2 master transmits a test pattern; MOSI (GPIO7) is wired to MISO (GPIO2),
 * so the same bytes echo back. Verifies SPI peripheral + bus integrity.
 * Requires Wire C: GPIO7 ↔ GPIO2 jumper.
 *
 * Pins:
 *   MOSI = GPIO7  (also safe_output on this board)
 *   MISO = GPIO2
 *   CLK  = GPIO6  (also safe_output on this board)
 *   CS   = GPIO10
 *
 * Patterns (on UART0 bridge, /dev/ttyACM0):
 *   AEL_SPI PASS   — TX and RX buffers match
 *   AEL_SPI FAIL   — mismatch (with per-byte detail)
 */

#include <stdio.h>
#include <string.h>
#include "driver/spi_master.h"
#include "driver/gpio.h"

#define PIN_MOSI   GPIO_NUM_7
#define PIN_MISO   GPIO_NUM_2
#define PIN_CLK    GPIO_NUM_6
#define PIN_CS     GPIO_NUM_10
#define SPI_FREQ   1000000   /* 1 MHz — conservative for wire */

static const uint8_t TX_DATA[] = {
    0xA5, 0x5A, 0xDE, 0xAD, 0xBE, 0xEF, 0x12, 0x34
};
#define DATA_LEN  ((int)sizeof(TX_DATA))

void app_main(void)
{
    /* Wait for UART observer to connect */
    vTaskDelay(pdMS_TO_TICKS(2000));

    spi_bus_config_t bus_cfg = {
        .mosi_io_num   = PIN_MOSI,
        .miso_io_num   = PIN_MISO,
        .sclk_io_num   = PIN_CLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = DATA_LEN,
    };
    spi_bus_initialize(SPI2_HOST, &bus_cfg, SPI_DMA_CH_AUTO);

    spi_device_interface_config_t dev_cfg = {
        .clock_speed_hz = SPI_FREQ,
        .mode           = 0,
        .spics_io_num   = PIN_CS,
        .queue_size     = 1,
    };
    spi_device_handle_t dev;
    spi_bus_add_device(SPI2_HOST, &dev_cfg, &dev);

    uint8_t rx_buf[DATA_LEN];
    memset(rx_buf, 0, sizeof(rx_buf));

    spi_transaction_t t = {
        .length    = DATA_LEN * 8,
        .tx_buffer = TX_DATA,
        .rx_buffer = rx_buf,
    };
    spi_device_transmit(dev, &t);

    int pass = (memcmp(TX_DATA, rx_buf, DATA_LEN) == 0);
    if (!pass) {
        for (int i = 0; i < DATA_LEN; i++) {
            printf("  [%d] tx=0x%02x rx=0x%02x%s\n",
                   i, TX_DATA[i], rx_buf[i],
                   TX_DATA[i] != rx_buf[i] ? " <-- MISMATCH" : "");
        }
    }
    for (int i = 0; i < 5; i++) {
        printf("AEL_SPI %s\n", pass ? "PASS" : "FAIL");
        vTaskDelay(pdMS_TO_TICKS(500));
    }

    spi_bus_remove_device(dev);
    spi_bus_free(SPI2_HOST);
}
