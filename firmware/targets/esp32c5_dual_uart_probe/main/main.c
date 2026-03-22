/*
 * esp32c5_dual_uart_probe  (role-verified edition)
 *
 * Each USB port receives EXCLUSIVE, role-specific messages.
 * No cross-mirroring. Proves not just connectivity but correct role assignment.
 *
 *   UART0 bridge  (GPIO11 TX → CH341 → /dev/ttyACM0)
 *     → "AEL_UART0 ..."   lines only — never seen on USB JTAG port
 *
 *   USB Serial/JTAG (GPIO13/14 → native USB → /dev/ttyACM3)
 *     → "AEL_USBJTAG ..." lines only — never seen on UART0 bridge port
 *
 * CONFIG_ESP_CONSOLE_NONE: both drivers installed and written explicitly.
 * printf() is unused; all output via uart_write_bytes / usb_serial_jtag_write_bytes.
 *
 * GPIO outputs (both ports show same GPIO state in their own banner):
 *   GPIO4: 1 kHz toggle
 *   GPIO5: 2 kHz toggle
 *   GPIO6: static high
 *   GPIO7: static low
 */

#include <stdint.h>
#include <string.h>
#include <stdio.h>

#include "driver/gpio.h"
#include "driver/uart.h"
#include "driver/usb_serial_jtag.h"
#include "esp_mac.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define UART0_BAUD   115200
#define UART0_TX     GPIO_NUM_11
#define UART0_RX     GPIO_NUM_12
#define UART0_BUF    256

/* Write a C string to UART0 */
static void u0(const char *s)
{
    uart_write_bytes(UART_NUM_0, s, strlen(s));
}

/* Write a C string to USB Serial/JTAG (50 ms timeout) */
static void uj(const char *s)
{
    usb_serial_jtag_write_bytes(s, strlen(s), pdMS_TO_TICKS(50));
}

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

    /* --- UART0 init --- */
    uart_config_t uart_cfg = {
        .baud_rate  = UART0_BAUD,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .flow_ctrl  = UART_HW_FLOWCTRL_DISABLE,
    };
    uart_param_config(UART_NUM_0, &uart_cfg);
    uart_set_pin(UART_NUM_0, UART0_TX, UART0_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    uart_driver_install(UART_NUM_0, UART0_BUF, 0, 0, NULL, 0);

    /* --- USB Serial/JTAG init --- */
    usb_serial_jtag_driver_config_t usb_cfg = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    usb_serial_jtag_driver_install(&usb_cfg);

    /* --- GPIO4-7 init --- */
    const gpio_num_t pins[4] = {GPIO_NUM_4, GPIO_NUM_5, GPIO_NUM_6, GPIO_NUM_7};
    for (int i = 0; i < 4; i++) {
        gpio_init_out(pins[i]);
        gpio_set_level(pins[i], 0);
    }
    gpio_set_level(pins[2], 1); /* GPIO6 high */
    gpio_set_level(pins[3], 0); /* GPIO7 low  */

    /* --- Boot banners: role-exclusive --- */
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);

    char buf[128];
    snprintf(buf, sizeof(buf),
             "AEL_UART0 ESP32C5  role=primary_uart  mac=%02x:%02x:%02x:%02x:%02x:%02x\n",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    u0(buf);
    u0("AEL_UART0 ESP32C5  gpio4=1kHz gpio5=2kHz gpio6=H gpio7=L\n");
    u0("AEL_UART0 ESP32C5  READY\n");

    snprintf(buf, sizeof(buf),
             "AEL_USBJTAG ESP32C5  role=usb_serial_jtag  mac=%02x:%02x:%02x:%02x:%02x:%02x\n",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    uj(buf);
    uj("AEL_USBJTAG ESP32C5  gpio4=1kHz gpio5=2kHz gpio6=H gpio7=L\n");
    uj("AEL_USBJTAG ESP32C5  READY\n");

    /* --- Main loop: GPIO toggle + periodic role banners --- */
    int64_t now       = esp_timer_get_time();
    int64_t next0     = now + 1000;
    int64_t next1     = now + 500;
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
            u0("AEL_UART0 ESP32C5  READY\n");
            uj("AEL_USBJTAG ESP32C5  READY\n");
        }
        if (now - last_yield >= 5000) {
            last_yield = now;
            taskYIELD();
        }
    }
}
