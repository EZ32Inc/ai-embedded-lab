#include <stdbool.h>
#include <stdio.h>
#include <stdint.h>

#include "hardware/gpio.h"
#include "pico/stdlib.h"

static volatile uint32_t g_irq_count = 0;

static void gpio_irq_cb(uint gpio, uint32_t events) {
    if (gpio == 17 && (events & GPIO_IRQ_EDGE_RISE)) {
        g_irq_count++;
    }
}

int main(void) {
    const uint LED_PIN = 25;
    const uint UART_TX_PIN = 0;
    const uint UART_RX_PIN = 1;
    const uint PULSE_OUT_PIN = 16;
    const uint IRQ_IN_PIN = 17;
    const uint TARGET_PULSES = 100;

    gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);

    stdio_init_all();
    sleep_ms(1200);

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);

    gpio_init(PULSE_OUT_PIN);
    gpio_set_dir(PULSE_OUT_PIN, GPIO_OUT);
    gpio_put(PULSE_OUT_PIN, 0);

    gpio_init(IRQ_IN_PIN);
    gpio_set_dir(IRQ_IN_PIN, GPIO_IN);
    gpio_pull_down(IRQ_IN_PIN);

    printf("AEL_READY RP2040 GPIO_IRQ BOOT\n");
    fflush(stdout);

    bool led = false;
    bool started = false;
    bool complete = false;
    uint64_t next_led_us = time_us_64() + 300000;
    uint64_t start_burst_us = time_us_64() + 3000000;
    uint64_t next_report_us = time_us_64() + 1000000;

    while (true) {
        uint64_t now = time_us_64();
        if (now >= next_led_us) {
            led = !led;
            gpio_put(LED_PIN, led);
            next_led_us += 300000;
        }

        if (!started && now >= start_burst_us) {
            gpio_set_irq_enabled_with_callback(IRQ_IN_PIN, GPIO_IRQ_EDGE_RISE, true, &gpio_irq_cb);
            started = true;
            printf("AEL_READY RP2040 GPIO_IRQ BURST\n");
            fflush(stdout);
            for (uint i = 0; i < TARGET_PULSES; ++i) {
                gpio_put(PULSE_OUT_PIN, 1);
                sleep_us(500);
                gpio_put(PULSE_OUT_PIN, 0);
                sleep_us(500);
            }
            sleep_ms(20);
            complete = true;
        }

        if (now >= next_report_us) {
            if (!started) {
                printf("AEL_READY RP2040 GPIO_IRQ WAIT\n");
            } else if (complete && g_irq_count == TARGET_PULSES) {
                printf("AEL_READY RP2040 GPIO_IRQ PASS count=%lu target=%u\n",
                       (unsigned long)g_irq_count, TARGET_PULSES);
            } else if (complete) {
                printf("AEL_READY RP2040 GPIO_IRQ FAIL count=%lu target=%u\n",
                       (unsigned long)g_irq_count, TARGET_PULSES);
            }
            fflush(stdout);
            next_report_us += 1000000;
        }

        tight_loop_contents();
    }
}
