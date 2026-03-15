/* {SLUG} — AEL draft firmware template (Group: rp)
 *
 * PLACEHOLDER: verify pin assignments for your board.
 *   Pico (RP2040): LED=25, adjust GPIO pins as needed.
 *   Pico 2 (RP2350): LED=25, same GPIO API.
 */
#include "pico/stdlib.h"

/* PLACEHOLDER: set LED and signature pins for your board */
#define AEL_LED_PIN   25u   /* PLACEHOLDER: onboard LED pin */
#define AEL_SIG_PIN0  16u   /* PLACEHOLDER: signature output pin 0 */
#define AEL_SIG_PIN1  17u   /* PLACEHOLDER: signature output pin 1 */

int main() {
    gpio_init(AEL_LED_PIN);
    gpio_set_dir(AEL_LED_PIN, GPIO_OUT);
    gpio_init(AEL_SIG_PIN0);
    gpio_set_dir(AEL_SIG_PIN0, GPIO_OUT);
    gpio_init(AEL_SIG_PIN1);
    gpio_set_dir(AEL_SIG_PIN1, GPIO_OUT);

    uint32_t t = 0;
    bool led = false;
    uint64_t next_led_us = time_us_64() + 300000;

    while (true) {
        gpio_put(AEL_SIG_PIN0, (t >> 0) & 1);
        gpio_put(AEL_SIG_PIN1, (t >> 1) & 1);

        uint64_t now = time_us_64();
        if (now >= next_led_us) {
            led = !led;
            gpio_put(AEL_LED_PIN, led);
            next_led_us = now + 300000;
        }
        t++;
    }
}
