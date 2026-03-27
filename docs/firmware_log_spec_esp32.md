# ESP32 Instrument Firmware Log Specification
# AEL Post-Flash Runtime Verification — Firmware Side Contract

## Core Principle

`flash success ≠ runtime ready`

AEL confirms that the firmware has actually reached its expected operational
state by reading the UART serial log.  For this to work reliably, the firmware
MUST output machine-readable log lines at predictable points in the boot
sequence.

---

## Required Log Sequence

The firmware must emit these lines **in this order** during startup.  Each line
must be on its own newline-terminated line.  Log level and tag prefix are
flexible (ESP_LOGI / printf), but the **payload keywords are fixed**.

```
I (nnn) ael: wifi connecting...
I (nnn) ael: wifi connected ssid=<SSID>
I (nnn) ael: ip=<x.x.x.x>
I (nnn) ael: server ready port=<N>
I (nnn) ael: AEL S3JTAGboard is OK
```

### Line-by-line requirements

| Line | Required keyword | Notes |
|------|-----------------|-------|
| WiFi connected | `wifi connected` or `sta connected` | Must appear before ip= |
| IP assigned | `ip=<addr>` | Exact format `ip=x.x.x.x`. Do not use "got IP" only (ambiguous) |
| Server ready | `server ready` or `Listening` or `gdb ready` or `ws ready` | At least one of these |
| Board OK | `AEL S3JTAGboard is OK` or `instrument ready` or `board ready` | This is the final "I am healthy" gate signal |

AEL's `instrument_ready` profile waits for all four groups.  If any group is
missing, the verification fails even if flash succeeded.

---

## Heartbeat

After the "board OK" line, the firmware **must** emit a heartbeat at regular
intervals.

```c
static void heartbeat_task(void *arg) {
    for (;;) {
        ESP_LOGI(TAG, "heartbeat");
        vTaskDelay(pdMS_TO_TICKS(3000));  // every 3 seconds
    }
}
```

**Why**: AEL waits a short confirmation window after the ready anchor and looks
for at least one heartbeat.  Without it, AEL cannot distinguish between "firmware
booted and is idle" and "firmware booted, printed OK, then immediately crashed".

Recommended interval: **3 seconds** (1 s is fine too; >10 s is not useful).

---

## Delays Between Critical Log Lines

ESP32 UART TX FIFO and USB CDC buffers can drop bytes if the firmware logs at
full speed.  Add a small `vTaskDelay` after each critical log line to ensure the
PC side receives it before the next burst.

```c
ESP_LOGI(TAG, "wifi connected ssid=%s", ssid);
vTaskDelay(pdMS_TO_TICKS(100));

ESP_LOGI(TAG, "ip=" IPSTR, IP2STR(&event->ip_info.ip));
vTaskDelay(pdMS_TO_TICKS(100));

ESP_LOGI(TAG, "server ready port=%d", SERVER_PORT);
vTaskDelay(pdMS_TO_TICKS(100));

ESP_LOGI(TAG, "AEL S3JTAGboard is OK");
vTaskDelay(pdMS_TO_TICKS(200));  // longer pause after the final gate line
```

Recommended delay: **50–200 ms** per critical line.

---

## Forbidden Patterns

AEL's `instrument_ready` profile treats any of the following as a runtime
failure regardless of what other lines appeared:

- `Guru Meditation`
- `panic`
- `assert failed`
- `abort()`
- `Brownout`
- `TWDT` / `Task watchdog`
- `LoadProhibited` / `StoreProhibited` / `InstrFetchProhibited` / `IllegalInstruction`
- `Rebooting...`

The firmware should **never suppress** these — they are fatal and must be
visible to AEL.

---

## Complete Minimal Reference Implementation

```c
// app_main.c  (ESP-IDF)

#define TAG "ael"

static void heartbeat_task(void *arg) {
    for (;;) {
        ESP_LOGI(TAG, "heartbeat");
        vTaskDelay(pdMS_TO_TICKS(3000));
    }
}

static void on_got_ip(void *arg, esp_event_base_t base,
                      int32_t id, void *data) {
    ip_event_got_ip_t *event = (ip_event_got_ip_t *)data;
    ESP_LOGI(TAG, "ip=" IPSTR, IP2STR(&event->ip_info.ip));
    vTaskDelay(pdMS_TO_TICKS(100));
}

void app_main(void) {
    // ... nvs, wifi init ...

    ESP_LOGI(TAG, "wifi connecting...");
    // ... wait for STA connected event ...
    ESP_LOGI(TAG, "wifi connected ssid=%s", ssid);
    vTaskDelay(pdMS_TO_TICKS(100));

    // ip= is emitted from on_got_ip callback (see above)

    // ... start server ...
    ESP_LOGI(TAG, "server ready port=%d", SERVER_PORT);
    vTaskDelay(pdMS_TO_TICKS(100));

    // Final gate line — AEL waits for this
    ESP_LOGI(TAG, "AEL S3JTAGboard is OK");
    vTaskDelay(pdMS_TO_TICKS(200));

    // Start heartbeat task
    xTaskCreate(heartbeat_task, "heartbeat", 2048, NULL, 1, NULL);

    // ... main application loop ...
}
```

---

## What AEL Does After Seeing These Lines

1. Matches all four required pattern groups.
2. Confirms at least one `heartbeat` line in a short window after `AEL S3JTAGboard is OK`.
3. Only then proceeds to network checks (ping, TCP :4242), WebSocket connection, and DUT tests.

If any step fails, AEL reports:
```
failure_kind: runtime_bringup_failed
error_summary: flash succeeded but runtime bring-up failed: missing patterns: [...]
```

This is never misreported as a network failure or instrument error.

---

## USB-UART Bridge RTS/DTR Reset Wiring Reminder

AEL uses DTR/RTS to reset the ESP32 into normal-boot mode:

| Signal | ESP32 pin | State during capture |
|--------|-----------|---------------------|
| DTR    | GPIO0 (BOOT) | **LOW** = keep HIGH (normal boot), so DTR must be de-asserted (False) |
| RTS    | EN (reset) | Pulse HIGH → LOW to reset; leave LOW (de-asserted) during capture |

AEL's `post_flash_verify` adapter always de-asserts DTR before opening the port
and before pulsing RTS, so the board boots in normal mode, not download mode.
