#include "pico/stdlib.h"

int main() {
    const uint LED_PIN = PICO_DEFAULT_LED_PIN;
    const uint PIN0 = 16;
    const uint PIN1 = 17;
    const uint PIN2 = 18;
    const uint PIN3 = 19;

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

    uint32_t t = 0;
    bool led = false;
    uint64_t next_led_us = time_us_64() + 300000;
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

        t++;
    }
}
