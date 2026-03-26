#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "hardware/gpio.h"
#include "hardware/spi.h"
#include "pico/stdlib.h"

int main(void) {
    const uint LED_PIN = 25;
    const uint UART_TX_PIN = 0;
    const uint UART_RX_PIN = 1;
    const uint SPI_SCK_PIN = 2;
    const uint SPI_TX_PIN = 3;
    const uint SPI_RX_PIN = 4;

    gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);

    stdio_init_all();
    sleep_ms(1200);

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);

    spi_init(spi0, 1000 * 1000);
    gpio_set_function(SPI_SCK_PIN, GPIO_FUNC_SPI);
    gpio_set_function(SPI_TX_PIN, GPIO_FUNC_SPI);
    gpio_set_function(SPI_RX_PIN, GPIO_FUNC_SPI);

    const uint8_t pattern[] = {0x55, 0xAA, 0x3C, 0xC3};
    uint8_t rx[sizeof(pattern)] = {0};
    unsigned pass_count = 0;
    bool led = false;
    uint64_t next_led_us = time_us_64() + 300000;
    uint64_t next_check_us = time_us_64() + 1000000;

    printf("AEL_READY RP2040 SPI BOOT\n");
    fflush(stdout);

    while (true) {
        uint64_t now = time_us_64();
        if (now >= next_led_us) {
            led = !led;
            gpio_put(LED_PIN, led);
            next_led_us = now + 300000;
        }
        if (now >= next_check_us) {
            memset(rx, 0, sizeof(rx));
            spi_write_read_blocking(spi0, pattern, rx, sizeof(pattern));
            if (memcmp(pattern, rx, sizeof(pattern)) == 0) {
                pass_count++;
                printf("AEL_READY RP2040 SPI PASS rx=%02X%02X%02X%02X count=%u\n",
                       rx[0], rx[1], rx[2], rx[3], pass_count);
            } else {
                printf("AEL_READY RP2040 SPI FAIL expect=%02X%02X%02X%02X got=%02X%02X%02X%02X\n",
                       pattern[0], pattern[1], pattern[2], pattern[3],
                       rx[0], rx[1], rx[2], rx[3]);
            }
            fflush(stdout);
            next_check_us = now + 1000000;
        }
    }
}
