#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/timer.h"

#include "ael_mailbox.h"

int main(void) {
    const uint led_pin = 25;
    uint32_t heartbeat = 0u;
    uint64_t next_toggle_us = time_us_64() + 250000u;
    bool led = false;

    gpio_init(led_pin);
    gpio_set_dir(led_pin, GPIO_OUT);
    gpio_put(led_pin, 0);

    ael_mailbox_init();
    sleep_ms(50);
    ael_mailbox_pass();

    while (true) {
        uint64_t now = time_us_64();
        if (now >= next_toggle_us) {
            led = !led;
            gpio_put(led_pin, led ? 1 : 0);
            next_toggle_us = now + 250000u;
            heartbeat += 1u;
            AEL_MAILBOX->detail0 = heartbeat;
        }
        tight_loop_contents();
    }
}
