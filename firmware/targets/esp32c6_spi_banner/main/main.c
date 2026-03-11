#include <stdio.h>
#include <stdint.h>

#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static void gpio_init_out(gpio_num_t pin) {
    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << pin,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
}

void app_main(void) {
    esp_task_wdt_deinit();

    const gpio_num_t pins[4] = {
        GPIO_NUM_4,
        GPIO_NUM_5,
        GPIO_NUM_6,
        GPIO_NUM_7,
    };

    for (int i = 0; i < 4; i++) {
        gpio_init_out(pins[i]);
        gpio_set_level(pins[i], 0);
    }
    gpio_set_level(pins[2], 1);

    spi_bus_config_t buscfg = {
        .mosi_io_num = GPIO_NUM_10,
        .miso_io_num = GPIO_NUM_2,
        .sclk_io_num = GPIO_NUM_11,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4,
    };
    spi_bus_initialize(SPI2_HOST, &buscfg, SPI_DMA_DISABLED);
    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 1000 * 1000,
        .mode = 0,
        .spics_io_num = GPIO_NUM_8,
        .queue_size = 1,
    };
    spi_device_handle_t spi = NULL;
    spi_bus_add_device(SPI2_HOST, &devcfg, &spi);

    printf("AEL_READY ESP32C6 SPI\n");

    int64_t now = esp_timer_get_time();
    int64_t next0 = now + 1000;
    int64_t next1 = now + 500;
    int64_t next_banner = now + 1000000;
    int64_t last_yield = now;
    uint8_t state0 = 0;
    uint8_t state1 = 0;
    uint8_t tx = 0x55;

    while (1) {
        now = esp_timer_get_time();
        if (now >= next0) {
            next0 += 1000;
            state0 ^= 1;
            gpio_set_level(pins[0], state0);
        }
        if (now >= next1) {
            next1 += 500;
            state1 ^= 1;
            gpio_set_level(pins[1], state1);
        }
        if (now >= next_banner) {
            spi_transaction_t t = {
                .length = 8,
                .tx_buffer = &tx,
            };
            spi_device_transmit(spi, &t);
            next_banner += 1000000;
            printf("AEL_READY ESP32C6 SPI tx=0x%02X\n", tx);
            tx++;
        }
        if (now - last_yield >= 5000) {
            last_yield = now;
            taskYIELD();
        }
    }
}
