#include "pico/stdlib.h"

int main() {
    const uint LED_PIN = 25; // Pico onboard LED
    const uint PINS[] = {16, 17, 18, 19};
    const size_t NUM_PINS = sizeof(PINS) / sizeof(PINS[0]);

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);

    for (size_t i = 0; i < NUM_PINS; i++) {
        gpio_init(PINS[i]);
        gpio_set_dir(PINS[i], GPIO_OUT);
        gpio_put(PINS[i], 0);
    }

    while (true) {
        gpio_put(LED_PIN, 1);
        for (size_t i = 0; i < NUM_PINS; i++) {
            gpio_put(PINS[i], 1);
        }
        sleep_ms(5);
        gpio_put(LED_PIN, 0);
        for (size_t i = 0; i < NUM_PINS; i++) {
            gpio_put(PINS[i], 0);
        }
        sleep_ms(5);
    }
}
