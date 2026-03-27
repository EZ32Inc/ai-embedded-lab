#include <stdio.h>

#include "hardware/gpio.h"
#include "hardware/pwm.h"
#include "pico/stdlib.h"

int main(void) {
    const uint LED_PIN = 25;
    const uint PWM_PIN = 18;
    const float DIVIDER = 125.0f;
    const uint16_t WRAP = 999;

    stdio_init_all();
    sleep_ms(1200);

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);

    gpio_set_function(PWM_PIN, GPIO_FUNC_PWM);
    uint slice = pwm_gpio_to_slice_num(PWM_PIN);
    pwm_config cfg = pwm_get_default_config();
    pwm_config_set_clkdiv(&cfg, DIVIDER);
    pwm_config_set_wrap(&cfg, WRAP);
    pwm_init(slice, &cfg, false);
    pwm_set_gpio_level(PWM_PIN, 500);
    pwm_set_enabled(slice, true);

    printf("AEL_READY RP2040 PWM GPIO18=1kHz duty=50%%\n");
    fflush(stdout);

    bool led = false;
    uint64_t next_led_us = time_us_64() + 300000;
    uint64_t next_banner_us = time_us_64() + 1000000;

    while (true) {
        uint64_t now = time_us_64();
        if (now >= next_led_us) {
            led = !led;
            gpio_put(LED_PIN, led);
            next_led_us += 300000;
        }
        if (now >= next_banner_us) {
            printf("AEL_READY RP2040 PWM GPIO18=1kHz duty=50%%\n");
            fflush(stdout);
            next_banner_us += 1000000;
        }
        tight_loop_contents();
    }
}
