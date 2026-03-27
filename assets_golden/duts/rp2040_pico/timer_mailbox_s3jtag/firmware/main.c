#include <stdbool.h>
#include <stdint.h>

#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/timer.h"

#include "ael_mailbox.h"

static volatile uint32_t g_tick_count = 0u;
static volatile bool g_passed = false;

static bool timer_cb(repeating_timer_t *rt) {
    (void)rt;
    uint32_t count = g_tick_count + 1u;
    g_tick_count = count;
    AEL_MAILBOX->detail0 = count;
    if (count >= 10u) {
        ael_mailbox_pass();
        g_passed = true;
        return false;
    }
    return true;
}

int main(void) {
    const uint led_pin = 25;
    bool led = false;
    uint32_t heartbeat = 0u;
    absolute_time_t next_toggle = make_timeout_time_ms(250);
    repeating_timer_t timer;

    gpio_init(led_pin);
    gpio_set_dir(led_pin, GPIO_OUT);
    gpio_put(led_pin, 0);

    ael_mailbox_init();
    if (!add_repeating_timer_ms(100, timer_cb, NULL, &timer)) {
        ael_mailbox_fail(1u, 0u);
        while (true) {
            tight_loop_contents();
        }
    }

    while (true) {
        if (absolute_time_diff_us(get_absolute_time(), next_toggle) <= 0) {
            led = !led;
            gpio_put(led_pin, led ? 1 : 0);
            next_toggle = delayed_by_ms(next_toggle, 250);
            heartbeat += 1u;
            if (g_passed) {
                AEL_MAILBOX->detail0 = (g_tick_count & 0xffffu) | ((heartbeat & 0xffffu) << 16);
            }
        }
        tight_loop_contents();
    }
}
