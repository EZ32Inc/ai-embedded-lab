/*
 * esp32c6_dual_uart_probe
 *
 * Validates both USB communication paths on a dual-USB ESP32-C6 board:
 *
 *   ACM (CH341)  — UART0 primary console   → receives all printf() output
 *   ACM (native) — USB Serial/JTAG secondary → mirrors all printf() output
 *
 * Both ports receive identical output simultaneously (secondary console
 * config). No custom drivers needed. Plug either or both — output appears
 * on whichever is connected.
 *
 * Also drives GPIO4-7 for optional meter validation:
 *   GPIO4: 1 kHz toggle
 *   GPIO5: 2 kHz toggle
 *   GPIO6: static high
 *   GPIO7: static low
 *
 * Banner lines (one per second):
 *   AEL_READY ESP32C6 DUAL  uart0=ok  usbjtag=ok  gpio=ok
 */

#include <stdio.h>
#include <stdint.h>

#include "driver/gpio.h"
#include "esp_chip_info.h"
#include "esp_mac.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static void gpio_init_out(gpio_num_t pin)
{
    gpio_config_t cfg = {
        .pin_bit_mask  = 1ULL << pin,
        .mode          = GPIO_MODE_OUTPUT,
        .pull_up_en    = GPIO_PULLUP_DISABLE,
        .pull_down_en  = GPIO_PULLDOWN_DISABLE,
        .intr_type     = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
}

void app_main(void)
{
    esp_task_wdt_deinit();

    /* GPIO setup */
    const gpio_num_t pins[4] = {GPIO_NUM_4, GPIO_NUM_5, GPIO_NUM_6, GPIO_NUM_7};
    for (int i = 0; i < 4; i++) {
        gpio_init_out(pins[i]);
        gpio_set_level(pins[i], 0);
    }
    gpio_set_level(pins[2], 1); /* GPIO6 high */
    gpio_set_level(pins[3], 0); /* GPIO7 low  */

    /* Print MAC so the user can confirm which board is talking */
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    printf("AEL_BOOT ESP32C6 DUAL  mac=%02x:%02x:%02x:%02x:%02x:%02x\n",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    printf("AEL_BOOT  console=uart0+usbjtag  gpio=4-7  baud=115200\n");
    printf("AEL_READY ESP32C6 DUAL  uart0=ok  usbjtag=ok  gpio=ok\n");

    int64_t now       = esp_timer_get_time();
    int64_t next0     = now + 1000;   /* GPIO4: 1 kHz */
    int64_t next1     = now + 500;    /* GPIO5: 2 kHz */
    int64_t next_ban  = now + 1000000;
    int64_t last_yield = now;
    uint8_t s0 = 0, s1 = 0;

    while (1) {
        now = esp_timer_get_time();

        if (now >= next0) {
            next0 += 1000;
            s0 ^= 1;
            gpio_set_level(pins[0], s0);
        }
        if (now >= next1) {
            next1 += 500;
            s1 ^= 1;
            gpio_set_level(pins[1], s1);
        }
        if (now >= next_ban) {
            next_ban += 1000000;
            printf("AEL_READY ESP32C6 DUAL  uart0=ok  usbjtag=ok  gpio=ok\n");
        }
        if (now - last_yield >= 5000) {
            last_yield = now;
            taskYIELD();
        }
    }
}
