#include "pico/stdlib.h"

int main(void) {
    const uint led_pin = 25;

    gpio_init(led_pin);
    gpio_set_dir(led_pin, GPIO_OUT);

    bool led = false;
    while (true) {
        led = !led;
        gpio_put(led_pin, led);
        sleep_ms(500);
    }
}
