#include <stdio.h>

#include "pico/stdlib.h"

int main(void) {
    const uint LED_PIN = 25;
    const uint SIGNAL_PIN = 16;
    const uint HALF_PERIOD_US = 5000;

    stdio_init_all();
    sleep_ms(1200);

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
    gpio_init(SIGNAL_PIN);
    gpio_set_dir(SIGNAL_PIN, GPIO_OUT);

    gpio_put(LED_PIN, 0);
    gpio_put(SIGNAL_PIN, 0);

    printf("AEL_READY RP2040 S3JTAG GPIO16=100Hz\n");
    fflush(stdout);

    bool led = false;
    bool signal = false;
    uint64_t next_signal_us = time_us_64() + HALF_PERIOD_US;
    uint64_t next_led_us = time_us_64() + 250000;
    uint64_t next_banner_us = time_us_64() + 1000000;

    while (true) {
        uint64_t now = time_us_64();
        if (now >= next_signal_us) {
            signal = !signal;
            gpio_put(SIGNAL_PIN, signal);
            next_signal_us += HALF_PERIOD_US;
        }
        if (now >= next_led_us) {
            led = !led;
            gpio_put(LED_PIN, led);
            next_led_us += 250000;
        }
        if (now >= next_banner_us) {
            printf("AEL_READY RP2040 S3JTAG GPIO16=100Hz\n");
            fflush(stdout);
            next_banner_us += 1000000;
        }
        tight_loop_contents();
    }
}
