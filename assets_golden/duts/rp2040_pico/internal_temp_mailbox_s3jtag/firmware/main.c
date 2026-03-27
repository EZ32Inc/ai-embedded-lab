#include <stdbool.h>
#include <stdint.h>

#include "hardware/adc.h"
#include "hardware/gpio.h"
#include "pico/stdlib.h"

#include "ael_mailbox.h"

enum {
    ERR_SAMPLE_ZERO = 0x1001u,
    ERR_SAMPLE_SAT = 0x1002u,
    ERR_SPREAD_ZERO = 0x1003u,
};

int main(void) {
    const uint LED_PIN = 25;
    const uint SAMPLE_COUNT = 8;
    uint16_t min_sample = 0xffffu;
    uint16_t max_sample = 0u;
    uint32_t sum = 0u;
    uint32_t heartbeat = 0u;
    bool led = false;
    uint64_t next_toggle_us = time_us_64() + 300000u;

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
    gpio_put(LED_PIN, 0);

    ael_mailbox_init();

    adc_init();
    adc_set_temp_sensor_enabled(true);
    adc_select_input(4);
    sleep_ms(20);

    for (uint i = 0; i < SAMPLE_COUNT; ++i) {
        uint16_t sample = adc_read();
        if (sample < min_sample) {
            min_sample = sample;
        }
        if (sample > max_sample) {
            max_sample = sample;
        }
        sum += sample;
        sleep_ms(5);
    }

    uint16_t avg_sample = (uint16_t)(sum / SAMPLE_COUNT);
    uint16_t spread = (uint16_t)(max_sample - min_sample);

    AEL_MAILBOX->detail0 = ((uint32_t)spread << 16) | avg_sample;

    if (avg_sample == 0u) {
        ael_mailbox_fail(ERR_SAMPLE_ZERO, AEL_MAILBOX->detail0);
    } else if (avg_sample >= 4095u) {
        ael_mailbox_fail(ERR_SAMPLE_SAT, AEL_MAILBOX->detail0);
    } else if (spread == 0u) {
        ael_mailbox_fail(ERR_SPREAD_ZERO, AEL_MAILBOX->detail0);
    } else {
        ael_mailbox_pass();
    }

    while (true) {
        uint64_t now = time_us_64();
        if (now >= next_toggle_us) {
            led = !led;
            gpio_put(LED_PIN, led ? 1 : 0);
            next_toggle_us = now + 300000u;
            heartbeat += 1u;
            AEL_MAILBOX->detail0 = (((uint32_t)spread << 16) | avg_sample) ^ heartbeat;
        }
        tight_loop_contents();
    }
}
