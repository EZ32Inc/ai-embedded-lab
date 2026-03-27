/*
 * timer_led_blink_ctrl_s3jtag — bidirectional LED blink control via AEL mailbox
 *
 * firmware → PC  (via GDB x/5xw 0x20041F00):
 *   detail0  bit[0]      = current led_state
 *            bits[15:1]  = toggle_count (wraps at 32767)
 *            bits[31:16] = active half-period (ms)
 *
 * PC → firmware  (via GDB: set {int}0x20041F10 = <half_period_ms>):
 *   Write desired half-period in ms to cmd_period_ms (offset 0x10).
 *   Firmware applies it on next tick and clears the field.
 *   Range: 50 – 5000 ms.  Default: 500 ms (1 Hz blink).
 */

#include <stdbool.h>
#include <stdint.h>

#include "hardware/gpio.h"
#include "hardware/timer.h"
#include "pico/stdlib.h"

#include "ael_mailbox.h"

#define LED_PIN          25u
#define TICK_MS          10u      /* timer fires every 10 ms                 */
#define DEFAULT_PERIOD   500u     /* half-period: 500 ms → 1 Hz blink        */
#define MIN_PERIOD       50u      /* fastest allowed half-period              */
#define MAX_PERIOD       5000u    /* slowest allowed half-period              */

static volatile uint32_t g_period_ms    = DEFAULT_PERIOD;
static volatile uint32_t g_elapsed_ms   = 0u;
static volatile bool     g_led_state    = false;
static volatile uint32_t g_toggle_count = 0u;

static bool timer_cb(repeating_timer_t *rt) {
    (void)rt;

    /* Check for period change command from PC */
    uint32_t cmd = AEL_MAILBOX->cmd_period_ms;
    if (cmd != 0u) {
        if (cmd < MIN_PERIOD) { cmd = MIN_PERIOD; }
        if (cmd > MAX_PERIOD) { cmd = MAX_PERIOD; }
        g_period_ms            = cmd;
        g_elapsed_ms           = 0u;   /* reset phase so change takes effect now */
        AEL_MAILBOX->cmd_period_ms = 0u; /* acknowledge — clear command */
    }

    /* Advance elapsed counter and toggle LED when due */
    g_elapsed_ms += TICK_MS;
    if (g_elapsed_ms >= g_period_ms) {
        g_elapsed_ms = 0u;
        g_led_state  = !g_led_state;
        gpio_put(LED_PIN, g_led_state ? 1 : 0);
        g_toggle_count = (g_toggle_count + 1u) & 0x7FFFu; /* 15-bit wrap */
    }

    /* Update detail0 for PC to read:
     *   bit[0]      = led_state
     *   bits[15:1]  = toggle_count
     *   bits[31:16] = active half-period in ms
     */
    AEL_MAILBOX->detail0 = (g_led_state ? 1u : 0u)
                         | (g_toggle_count << 1)
                         | ((g_period_ms & 0xFFFFu) << 16);

    return true; /* keep repeating */
}

int main(void) {
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
    gpio_put(LED_PIN, 0);

    ael_mailbox_init();

    repeating_timer_t timer;
    if (!add_repeating_timer_ms(TICK_MS, timer_cb, NULL, &timer)) {
        ael_mailbox_fail(1u, 0u);
        while (true) { tight_loop_contents(); }
    }

    /* LED is driven entirely from the timer ISR — main loop idles */
    while (true) {
        tight_loop_contents();
    }
}
