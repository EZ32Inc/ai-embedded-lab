"""
ael.patterns.loopback.pcnt_loopback
=====================================
Reusable pattern for on-board PCNT pulse-count loopback validation.

Background
----------
The PCNT loopback is the simplest instrument-free electrical verification
that can be performed on a new ESP32 board:

  GPIO_DRIVE (output) ──jumper── GPIO_INPUT (PCNT counter input)

The firmware drives N rising edges on GPIO_DRIVE and the PCNT hardware
counts them on GPIO_INPUT.  A counted == sent result proves:

  1. GPIO output drive level is correct (digital signal intact).
  2. GPIO input sampling works (internal peripheral functional).
  3. MCU real-time timing is correct (busy-delay pulse generation).

This requires exactly one jumper wire and zero external instruments.

Validated on
------------
  ESP32-C6  GPIO20 → GPIO21   100/100  (esp32c6_suite_ext)
  ESP32-C5  GPIO2  → GPIO3    100/100  (esp32c5_suite_ext)

Usage
-----
1. Generate C firmware snippet:
       code = pcnt_loopback_c_snippet(drive_gpio=2, input_gpio=3, pulses=100)
       print(code)

2. Parse test result from UART line:
       ok, info = parse_pcnt_result("AEL_PCNT sent=100 counted=100 PASS")
       assert ok

3. Verify expected pin pair for a board:
       validate_pin_pair("esp32c5", 2, 3)   # raises if invalid
"""

from __future__ import annotations
import re

# ── Known validated pin pairs ─────────────────────────────────────────────────
# Maps chip → list of (drive_gpio, input_gpio) pairs that have been
# physically verified to work as a PCNT loopback.
VALIDATED_PAIRS: dict[str, list[tuple[int, int]]] = {
    "esp32c6": [(20, 21)],
    "esp32c5": [(2, 3)],
}

# ── Pattern metadata ──────────────────────────────────────────────────────────
PATTERN_NAME        = "pcnt_loopback"
PATTERN_VERSION     = "1.0"
REQUIRED_WIRING     = "1 jumper wire between GPIO_DRIVE and GPIO_INPUT"
UART_TAG            = "AEL_PCNT"
UART_PATTERN        = r"AEL_PCNT sent=(\d+) counted=(\d+) (PASS|FAIL)"
DEFAULT_PULSE_COUNT = 100
PULSE_HALF_PERIOD_US = 10   # µs per half-period — safe for all ESP32 targets


def validate_pin_pair(chip: str, drive: int, input_gpio: int) -> None:
    """
    Raise ValueError if the given (drive, input_gpio) pair has not been
    validated for the chip.  Pass to skip validation.
    """
    known = VALIDATED_PAIRS.get(chip.lower())
    if known is None:
        return   # no data for this chip — allow, caller's responsibility
    if (drive, input_gpio) not in known:
        raise ValueError(
            f"Pin pair GPIO{drive}→GPIO{input_gpio} not in validated list "
            f"for {chip}: {known}.  Add it after physical verification."
        )


def parse_pcnt_result(line: str) -> tuple[bool, dict]:
    """
    Parse a UART line containing an AEL_PCNT result.

    Returns (ok, info_dict) where info_dict has keys:
      sent, counted, verdict

    Returns (False, {}) if the line does not match.
    """
    m = re.search(UART_PATTERN, line)
    if not m:
        return False, {}
    sent    = int(m.group(1))
    counted = int(m.group(2))
    verdict = m.group(3)
    ok = (verdict == "PASS") and (counted == sent)
    return ok, {"sent": sent, "counted": counted, "verdict": verdict}


def pcnt_loopback_c_snippet(
    drive_gpio: int,
    input_gpio: int,
    pulses: int = DEFAULT_PULSE_COUNT,
    half_period_us: int = PULSE_HALF_PERIOD_US,
) -> str:
    """
    Generate a self-contained C code snippet implementing the PCNT loopback
    test for the given GPIO pair.

    The snippet assumes the following headers are already included:
      driver/gpio.h, driver/pulse_cnt.h, esp_timer.h, freertos/FreeRTOS.h

    Paste into app_main() or a test function after nvs_flash_init().
    """
    return f"""\
/* ── PCNT loopback: GPIO{drive_gpio} → GPIO{input_gpio}, {pulses} pulses ── */
static void busy_delay_us_{drive_gpio}(uint32_t us) {{
    int64_t end = esp_timer_get_time() + (int64_t)us;
    while (esp_timer_get_time() < end) {{}}
}}

{{
    /* configure drive pin */
    gpio_config_t _gc = {{
        .pin_bit_mask = 1ULL << GPIO_NUM_{drive_gpio},
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    }};
    gpio_config(&_gc);
    gpio_set_level(GPIO_NUM_{drive_gpio}, 0);

    /* configure PCNT */
    pcnt_unit_config_t _ucfg = {{ .low_limit = -1, .high_limit = {pulses * 2} }};
    pcnt_unit_handle_t _unit = NULL;
    pcnt_new_unit(&_ucfg, &_unit);

    pcnt_chan_config_t _ccfg = {{
        .edge_gpio_num  = GPIO_NUM_{input_gpio},
        .level_gpio_num = -1,
    }};
    pcnt_channel_handle_t _chan = NULL;
    pcnt_new_channel(_unit, &_ccfg, &_chan);

    pcnt_channel_set_edge_action(_chan,
        PCNT_CHANNEL_EDGE_ACTION_INCREASE,
        PCNT_CHANNEL_EDGE_ACTION_HOLD);
    pcnt_channel_set_level_action(_chan,
        PCNT_CHANNEL_LEVEL_ACTION_KEEP,
        PCNT_CHANNEL_LEVEL_ACTION_KEEP);

    pcnt_unit_enable(_unit);
    pcnt_unit_clear_count(_unit);
    pcnt_unit_start(_unit);

    for (int _i = 0; _i < {pulses}; _i++) {{
        gpio_set_level(GPIO_NUM_{drive_gpio}, 1);
        busy_delay_us_{drive_gpio}({half_period_us});
        gpio_set_level(GPIO_NUM_{drive_gpio}, 0);
        busy_delay_us_{drive_gpio}({half_period_us});
    }}
    vTaskDelay(pdMS_TO_TICKS(10));

    int _count = 0;
    pcnt_unit_get_count(_unit, &_count);
    pcnt_unit_stop(_unit);
    pcnt_unit_disable(_unit);

    int _ok = (_count == {pulses});
    printf("AEL_PCNT sent={pulses} counted=%d %s\\n",
           _count, _ok ? "PASS" : "FAIL");
}}
/* ── end PCNT loopback ── */
"""
