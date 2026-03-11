#include <stdio.h>

#include "hardware/i2c.h"
#include "pico/stdlib.h"

int main(void) {
    const uint LED_PIN = 25;
    const uint PIN0 = 16;
    const uint PIN1 = 17;
    const uint PIN2 = 18;
    const uint PIN3 = 19;

    stdio_init_all();
    sleep_ms(1200);

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
    gpio_init(PIN0);
    gpio_set_dir(PIN0, GPIO_OUT);
    gpio_init(PIN1);
    gpio_set_dir(PIN1, GPIO_OUT);
    gpio_init(PIN2);
    gpio_set_dir(PIN2, GPIO_OUT);
    gpio_init(PIN3);
    gpio_set_dir(PIN3, GPIO_OUT);

    i2c_init(i2c0, 100 * 1000);
    gpio_set_function(4, GPIO_FUNC_I2C);
    gpio_set_function(5, GPIO_FUNC_I2C);
    gpio_pull_up(4);
    gpio_pull_up(5);

    printf("AEL_READY RP2040 I2C\n");
    fflush(stdout);

    uint8_t payload = 0x33;
    uint32_t t = 0;
    bool led = false;
    uint64_t next_led_us = time_us_64() + 300000;
    uint64_t next_banner_us = time_us_64() + 1000000;
    while (true) {
        gpio_put(PIN0, (t >> 0) & 1);
        gpio_put(PIN1, (t >> 1) & 1);
        gpio_put(PIN2, (t >> 2) & 1);
        gpio_put(PIN3, (t >> 3) & 1);

        uint64_t now = time_us_64();
        if (now >= next_led_us) {
            led = !led;
            gpio_put(LED_PIN, led);
            next_led_us = now + 300000;
        }
        if (now >= next_banner_us) {
            i2c_write_timeout_us(i2c0, 0x42, &payload, 1, true, 2000);
            printf("AEL_READY RP2040 I2C tx=0x%02X\n", payload);
            fflush(stdout);
            payload++;
            next_banner_us = now + 1000000;
        }

        t++;
    }
}
