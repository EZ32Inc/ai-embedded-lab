#include <stdbool.h>
#include <stdint.h>

#include "hardware/adc.h"
#include "hardware/gpio.h"
#include "pico/stdlib.h"

#include "ael_mailbox.h"

#define ADC_GPIO        26u
#define DRIVE_GPIO      22u
#define SAMPLE_COUNT    8u
#define HIGH_THRESHOLD  3800u
#define LOW_THRESHOLD   300u

enum {
    ERR_HIGH_TOO_LOW = 0x2001u,
    ERR_LOW_TOO_HIGH = 0x2002u,
};

static uint16_t sample_avg(void) {
    uint32_t sum = 0u;
    for (uint i = 0u; i < SAMPLE_COUNT; ++i) {
        sum += adc_read();
        sleep_ms(2);
    }
    return (uint16_t)(sum / SAMPLE_COUNT);
}

int main(void) {
    const uint LED_PIN = 25u;
    bool led = false;
    uint32_t heartbeat = 0u;
    uint64_t next_toggle_us;

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
    gpio_put(LED_PIN, 0);

    ael_mailbox_init();

    gpio_init(DRIVE_GPIO);
    gpio_set_dir(DRIVE_GPIO, GPIO_OUT);
    gpio_put(DRIVE_GPIO, 0);

    adc_init();
    adc_gpio_init(ADC_GPIO);
    adc_select_input(0);
    sleep_ms(20);

    gpio_put(DRIVE_GPIO, 1);
    sleep_ms(10);
    uint16_t high_avg = sample_avg();

    gpio_put(DRIVE_GPIO, 0);
    sleep_ms(10);
    uint16_t low_avg = sample_avg();

    uint32_t detail = ((uint32_t)high_avg << 16) | low_avg;
    AEL_MAILBOX->detail0 = detail;

    if (high_avg < HIGH_THRESHOLD) {
        ael_mailbox_fail(ERR_HIGH_TOO_LOW, detail);
    } else if (low_avg > LOW_THRESHOLD) {
        ael_mailbox_fail(ERR_LOW_TOO_HIGH, detail);
    } else {
        ael_mailbox_pass();
    }

    next_toggle_us = time_us_64() + 300000u;
    while (true) {
        uint64_t now = time_us_64();
        if (now >= next_toggle_us) {
            led = !led;
            gpio_put(LED_PIN, led ? 1u : 0u);
            next_toggle_us = now + 300000u;
            heartbeat += 1u;
            AEL_MAILBOX->detail0 = detail ^ heartbeat;
        }
        tight_loop_contents();
    }
}
