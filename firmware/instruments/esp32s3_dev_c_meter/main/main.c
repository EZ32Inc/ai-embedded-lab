#include <ctype.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "driver/gpio.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_rom_sys.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"

#define WIFI_PASS "esp32gpiom"
#define WIFI_PORT 9000
#define MAX_LINE 256

static const char *TAG = "AEL_METER";

static const int k_in_pins[4] = {11, 12, 13, 14};
static const int k_out_pins[4] = {15, 16, 17, 18};

static adc_oneshot_unit_handle_t s_adc_handle = NULL;
static adc_cali_handle_t s_adc_cali = NULL;

typedef struct {
    int gpio;
    int samples;
    int ones;
    int zeros;
    int transitions;
    const char *state;
} digital_stats_t;

static const int k_selftest_toggle_min_transitions = 10;

static void make_ssid(char *out, size_t out_len, uint8_t *mac) {
    unsigned int last = ((unsigned int)mac[4] << 8) | mac[5];
    snprintf(out, out_len, "ESP32_GPIO_METER_%04X", last & 0xFFFFu);
}

static void wifi_init_softap(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    wifi_config_t wifi_config = {0};
    uint8_t mac[6] = {0};
    esp_read_mac(mac, ESP_MAC_WIFI_SOFTAP);
    make_ssid((char *)wifi_config.ap.ssid, sizeof(wifi_config.ap.ssid), mac);
    wifi_config.ap.ssid_len = strlen((char *)wifi_config.ap.ssid);
    strncpy((char *)wifi_config.ap.password, WIFI_PASS, sizeof(wifi_config.ap.password) - 1);
    wifi_config.ap.max_connection = 4;
    wifi_config.ap.authmode = WIFI_AUTH_WPA_WPA2_PSK;
    if (strlen(WIFI_PASS) == 0) {
        wifi_config.ap.authmode = WIFI_AUTH_OPEN;
    }

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "SoftAP SSID: %s", (char *)wifi_config.ap.ssid);
    ESP_LOGI(TAG, "SoftAP password: %s", WIFI_PASS);
    ESP_LOGI(TAG, "TCP port: %d", WIFI_PORT);
}

static void adc_init(void) {
    adc_oneshot_unit_init_cfg_t init_cfg = {
        .unit_id = ADC_UNIT_1,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&init_cfg, &s_adc_handle));

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = ADC_ATTEN_DB_11,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(s_adc_handle, ADC_CHANNEL_3, &chan_cfg));

    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = ADC_UNIT_1,
        .atten = ADC_ATTEN_DB_11,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    if (adc_cali_create_scheme_curve_fitting(&cali_cfg, &s_adc_cali) != ESP_OK) {
        s_adc_cali = NULL;
    }
}

static void gpio_init_defaults(void) {
    for (size_t i = 0; i < 4; i++) {
        gpio_reset_pin(k_in_pins[i]);
        gpio_set_direction(k_in_pins[i], GPIO_MODE_INPUT);
        gpio_set_pull_mode(k_in_pins[i], GPIO_FLOATING);
    }
    for (size_t i = 0; i < 4; i++) {
        gpio_reset_pin(k_out_pins[i]);
        gpio_set_direction(k_out_pins[i], GPIO_MODE_INPUT);
        gpio_set_pull_mode(k_out_pins[i], GPIO_FLOATING);
    }
}

static int parse_int(const char *s, int def_val) {
    if (!s) {
        return def_val;
    }
    return atoi(s);
}

static const char *find_kv(const char *line, const char *key) {
    const char *p = line;
    size_t klen = strlen(key);
    while ((p = strstr(p, key)) != NULL) {
        if ((p == line || isspace((unsigned char)p[-1])) && p[klen] == '=') {
            return p + klen + 1;
        }
        p += klen;
    }
    return NULL;
}

static void send_json(int sock, const char *json) {
    if (!json) {
        return;
    }
    send(sock, json, strlen(json), 0);
    send(sock, "\n", 1, 0);
}

static void handle_ping(int sock) {
    uint8_t mac[6] = {0};
    esp_read_mac(mac, ESP_MAC_WIFI_SOFTAP);
    char ssid[32] = {0};
    make_ssid(ssid, sizeof(ssid), mac);
    char buf[256];
    snprintf(
        buf,
        sizeof(buf),
        "{\"ok\":true,\"type\":\"pong\",\"fw\":\"v0.1\",\"mac\":\"%02X:%02X:%02X:%02X:%02X:%02X\","
        "\"ssid\":\"%s\",\"ip\":\"192.168.4.1\",\"port\":%d}",
        mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], ssid, WIFI_PORT);
    send_json(sock, buf);
}

static const char *classify_digital_state(int ones, int zeros) {
    if (ones == 0) {
        return "low";
    }
    if (zeros == 0) {
        return "high";
    }
    return "toggle";
}

static void measure_digital_gpio(int gpio, int duration_ms, digital_stats_t *out) {
    if (!out) {
        return;
    }
    out->gpio = gpio;
    out->samples = 0;
    out->ones = 0;
    out->zeros = 0;
    out->transitions = 0;
    out->state = "toggle";

    int last = -1;
    int64_t end = esp_timer_get_time() + ((int64_t)duration_ms * 1000);
    while (esp_timer_get_time() < end) {
        int v = gpio_get_level(gpio);
        out->samples++;
        if (v) {
            out->ones++;
        } else {
            out->zeros++;
        }
        if (last >= 0 && v != last) {
            out->transitions++;
        }
        last = v;
    }
    out->state = classify_digital_state(out->ones, out->zeros);
}

static void handle_meas_digital(int sock, const char *line) {
    int duration_ms = parse_int(find_kv(line, "DUR_MS"), 500);
    digital_stats_t stats[4];
    for (int i = 0; i < 4; i++) {
        measure_digital_gpio(k_in_pins[i], duration_ms, &stats[i]);
    }

    char buf[512];
    int n = snprintf(buf, sizeof(buf), "{\"ok\":true,\"type\":\"digital\",\"duration_ms\":%d,\"pins\":[", duration_ms);
    for (int i = 0; i < 4; i++) {
        n += snprintf(
            buf + n,
            sizeof(buf) - n,
            "{\"gpio\":%d,\"state\":\"%s\",\"samples\":%d,\"ones\":%d,\"zeros\":%d,\"transitions\":%d}%s",
            stats[i].gpio,
            stats[i].state,
            stats[i].samples,
            stats[i].ones,
            stats[i].zeros,
            stats[i].transitions,
            (i == 3) ? "" : ",");
    }
    snprintf(buf + n, sizeof(buf) - n, "]}");
    send_json(sock, buf);
}

static float measure_voltage_gpio4(int avg, int *raw_avg_out, bool *cali_used_out) {
    int total = 0;
    int reads = 0;
    for (int i = 0; i < avg; i++) {
        int raw = 0;
        if (adc_oneshot_read(s_adc_handle, ADC_CHANNEL_3, &raw) == ESP_OK) {
            total += raw;
            reads++;
        }
    }
    int raw_avg = reads > 0 ? total / reads : 0;
    int mv = raw_avg;
    bool cali_used = false;
    if (s_adc_cali) {
        if (adc_cali_raw_to_voltage(s_adc_cali, raw_avg, &mv) == ESP_OK) {
            cali_used = true;
        }
    }
    if (!cali_used) {
        mv = (raw_avg * 3300) / 4095;
    }
    if (raw_avg_out) {
        *raw_avg_out = raw_avg;
    }
    if (cali_used_out) {
        *cali_used_out = cali_used;
    }
    return ((float)mv) / 1000.0f;
}

static void handle_meas_voltage(int sock, const char *line) {
    int avg = parse_int(find_kv(line, "AVG"), 16);
    float volts = measure_voltage_gpio4(avg, NULL, NULL);
    char buf[192];
    snprintf(
        buf,
        sizeof(buf),
        "{\"ok\":true,\"type\":\"voltage\",\"gpio\":4,\"voltage_v\":%.3f,\"avg\":%d,\"unit\":\"V\"}",
        volts,
        avg);
    send_json(sock, buf);
}

static bool is_out_gpio(int gpio) {
    for (int i = 0; i < 4; i++) {
        if (k_out_pins[i] == gpio) {
            return true;
        }
    }
    return false;
}

static void set_hiz(int gpio) {
    gpio_set_direction(gpio, GPIO_MODE_INPUT);
    gpio_set_pull_mode(gpio, GPIO_FLOATING);
}

static void handle_stim_digital(int sock, const char *line) {
    int gpio = parse_int(find_kv(line, "GPIO"), -1);
    const char *mode = find_kv(line, "MODE");
    int duration_us = parse_int(find_kv(line, "DUR_US"), 0);
    int freq_hz = parse_int(find_kv(line, "FREQ_HZ"), 1000);
    const char *pattern = find_kv(line, "PATTERN");
    int keep = parse_int(find_kv(line, "KEEP"), 0);

    if (!is_out_gpio(gpio)) {
        send_json(sock, "{\"ok\":false,\"error\":\"gpio_not_supported\"}");
        return;
    }
    if (!mode) {
        send_json(sock, "{\"ok\":false,\"error\":\"mode_missing\"}");
        return;
    }

    if (strcmp(mode, "hiz") == 0) {
        set_hiz(gpio);
    } else if (strcmp(mode, "low") == 0 || strcmp(mode, "high") == 0) {
        gpio_set_direction(gpio, GPIO_MODE_OUTPUT);
        gpio_set_level(gpio, strcmp(mode, "high") == 0 ? 1 : 0);
    } else if (strcmp(mode, "toggle") == 0) {
        gpio_set_direction(gpio, GPIO_MODE_OUTPUT);
        int level = 0;
        int64_t start = esp_timer_get_time();
        int64_t end = start + duration_us;
        int period_us = freq_hz > 0 ? (1000000 / freq_hz) : 1000;
        if (period_us < 2) {
            period_us = 2;
        }
        while (esp_timer_get_time() < end) {
            level = !level;
            gpio_set_level(gpio, level);
            esp_rom_delay_us(period_us / 2);
        }
    } else if (strcmp(mode, "pulse") == 0) {
        gpio_set_direction(gpio, GPIO_MODE_OUTPUT);
        if (!pattern) {
            pattern = "lhl";
        }
        int segment = duration_us / 3;
        for (int i = 0; i < 3; i++) {
            char c = pattern[i];
            gpio_set_level(gpio, (c == 'h' || c == 'H') ? 1 : 0);
            esp_rom_delay_us(segment);
        }
    } else {
        send_json(sock, "{\"ok\":false,\"error\":\"mode_not_supported\"}");
        return;
    }

    if (!keep) {
        set_hiz(gpio);
    }

    char buf[196];
    snprintf(
        buf,
        sizeof(buf),
        "{\"ok\":true,\"type\":\"stim\",\"gpio\":%d,\"mode\":\"%s\",\"duration_us\":%d,\"freq_hz\":%d,"
        "\"final\":\"%s\"}",
        gpio,
        mode,
        duration_us,
        freq_hz,
        keep ? "keep" : "hiz");
    send_json(sock, buf);
}

static bool is_in_gpio(int gpio) {
    for (int i = 0; i < 4; i++) {
        if (k_in_pins[i] == gpio) {
            return true;
        }
    }
    return false;
}

static void handle_selftest(int sock, const char *line) {
    int out_gpio = parse_int(find_kv(line, "OUT"), 15);
    int in_gpio = parse_int(find_kv(line, "IN"), 11);
    int adc_out_gpio = parse_int(find_kv(line, "ADC_OUT"), 16);
    int adc_in_gpio = parse_int(find_kv(line, "ADC_IN"), 4);
    int duration_ms = parse_int(find_kv(line, "DUR_MS"), 200);
    int freq_hz = parse_int(find_kv(line, "FREQ_HZ"), 1000);
    int settle_ms = parse_int(find_kv(line, "SETTLE_MS"), 20);
    int avg = parse_int(find_kv(line, "AVG"), 16);
    int keep = parse_int(find_kv(line, "KEEP"), 0);

    if (!is_out_gpio(out_gpio) || !is_in_gpio(in_gpio) || !is_out_gpio(adc_out_gpio) || adc_in_gpio != 4) {
        send_json(
            sock,
            "{\"ok\":true,\"type\":\"selftest\",\"pass\":false,\"error\":\"gpio_not_supported\"}");
        return;
    }

    if (duration_ms < 20) {
        duration_ms = 20;
    }
    if (settle_ms < 1) {
        settle_ms = 1;
    }
    if (avg < 1) {
        avg = 1;
    }

    ESP_LOGI(
        TAG,
        "SELFTEST start out=%d in=%d adc_out=%d adc_in=%d dur_ms=%d freq_hz=%d avg=%d settle_ms=%d",
        out_gpio,
        in_gpio,
        adc_out_gpio,
        adc_in_gpio,
        duration_ms,
        freq_hz,
        avg,
        settle_ms);

    set_hiz(out_gpio);
    set_hiz(adc_out_gpio);

    digital_stats_t low_stats = {0};
    digital_stats_t high_stats = {0};
    digital_stats_t toggle_stats = {0};

    gpio_set_direction(in_gpio, GPIO_MODE_INPUT);
    gpio_set_pull_mode(in_gpio, GPIO_FLOATING);
    gpio_set_direction(out_gpio, GPIO_MODE_OUTPUT);

    gpio_set_level(out_gpio, 0);
    esp_rom_delay_us((uint32_t)settle_ms * 1000);
    measure_digital_gpio(in_gpio, settle_ms * 2, &low_stats);

    gpio_set_level(out_gpio, 1);
    esp_rom_delay_us((uint32_t)settle_ms * 1000);
    measure_digital_gpio(in_gpio, settle_ms * 2, &high_stats);

    int period_us = freq_hz > 0 ? (1000000 / freq_hz) : 1000;
    if (period_us < 2) {
        period_us = 2;
    }
    toggle_stats.gpio = in_gpio;
    toggle_stats.samples = 0;
    toggle_stats.ones = 0;
    toggle_stats.zeros = 0;
    toggle_stats.transitions = 0;
    toggle_stats.state = "toggle";
    int last = gpio_get_level(in_gpio);
    int level = 0;
    gpio_set_level(out_gpio, level);

    int64_t end = esp_timer_get_time() + ((int64_t)duration_ms * 1000);
    while (esp_timer_get_time() < end) {
        level = !level;
        gpio_set_level(out_gpio, level);
        esp_rom_delay_us(period_us / 2);

        int v = gpio_get_level(in_gpio);
        toggle_stats.samples++;
        if (v) {
            toggle_stats.ones++;
        } else {
            toggle_stats.zeros++;
        }
        if (v != last) {
            toggle_stats.transitions++;
        }
        last = v;
    }
    toggle_stats.state = classify_digital_state(toggle_stats.ones, toggle_stats.zeros);

    bool digital_pass = (strcmp(low_stats.state, "low") == 0) && (strcmp(high_stats.state, "high") == 0) &&
                        (strcmp(toggle_stats.state, "toggle") == 0) &&
                        (toggle_stats.transitions > k_selftest_toggle_min_transitions);

    gpio_set_direction(adc_out_gpio, GPIO_MODE_OUTPUT);
    gpio_set_level(adc_out_gpio, 0);
    esp_rom_delay_us((uint32_t)settle_ms * 1000);
    bool cali_used_low = false;
    bool cali_used_high = false;
    float v_low = measure_voltage_gpio4(avg, NULL, &cali_used_low);

    gpio_set_level(adc_out_gpio, 1);
    esp_rom_delay_us((uint32_t)settle_ms * 1000);
    float v_high = measure_voltage_gpio4(avg, NULL, &cali_used_high);

    bool cali_used = cali_used_low || cali_used_high;
    float v_low_max = cali_used ? 0.30f : 0.50f;
    float v_high_min = cali_used ? 2.60f : 2.20f;
    bool adc_pass = (v_low < v_low_max) && (v_high > v_high_min);

    if (!keep) {
        set_hiz(out_gpio);
        set_hiz(adc_out_gpio);
    }

    bool pass = digital_pass && adc_pass;
    const char *error = "";
    if (!digital_pass) {
        if (strcmp(low_stats.state, "low") != 0) {
            error = "digital_low_failed";
        } else if (strcmp(high_stats.state, "high") != 0) {
            error = "digital_high_failed";
        } else if (strcmp(toggle_stats.state, "toggle") != 0) {
            error = "digital_toggle_state_failed";
        } else {
            error = "digital_toggle_transitions_low";
        }
    } else if (!adc_pass) {
        if (v_low >= v_low_max) {
            error = "adc_low_voltage_too_high";
        } else if (v_high <= v_high_min) {
            error = "adc_high_voltage_too_low";
        } else {
            error = "adc_window_failed";
        }
    }

    ESP_LOGI(
        TAG,
        "SELFTEST result pass=%d digital_pass=%d adc_pass=%d v_low=%.3f v_high=%.3f",
        pass ? 1 : 0,
        digital_pass ? 1 : 0,
        adc_pass ? 1 : 0,
        v_low,
        v_high);

    char buf[1400];
    int n = snprintf(
        buf,
        sizeof(buf),
        "{\"ok\":true,\"type\":\"selftest\",\"pass\":%s",
        pass ? "true" : "false");
    if (!pass) {
        n += snprintf(buf + n, sizeof(buf) - n, ",\"error\":\"%s\"", error);
    }
    n += snprintf(
        buf + n,
        sizeof(buf) - n,
        ",\"digital\":{\"pass\":%s,\"out_gpio\":%d,\"in_gpio\":%d,\"dur_ms\":%d,\"freq_hz\":%d,"
        "\"low\":{\"state\":\"%s\",\"samples\":%d,\"ones\":%d,\"zeros\":%d,\"transitions\":%d},"
        "\"high\":{\"state\":\"%s\",\"samples\":%d,\"ones\":%d,\"zeros\":%d,\"transitions\":%d},"
        "\"toggle\":{\"state\":\"%s\",\"samples\":%d,\"ones\":%d,\"zeros\":%d,\"transitions\":%d}},"
        "\"adc\":{\"pass\":%s,\"out_gpio\":%d,\"adc_gpio\":%d,\"avg\":%d,\"settle_ms\":%d,"
        "\"v_low\":%.3f,\"v_high\":%.3f}}",
        digital_pass ? "true" : "false",
        out_gpio,
        in_gpio,
        duration_ms,
        freq_hz,
        low_stats.state,
        low_stats.samples,
        low_stats.ones,
        low_stats.zeros,
        low_stats.transitions,
        high_stats.state,
        high_stats.samples,
        high_stats.ones,
        high_stats.zeros,
        high_stats.transitions,
        toggle_stats.state,
        toggle_stats.samples,
        toggle_stats.ones,
        toggle_stats.zeros,
        toggle_stats.transitions,
        adc_pass ? "true" : "false",
        adc_out_gpio,
        adc_in_gpio,
        avg,
        settle_ms,
        v_low,
        v_high);
    send_json(sock, buf);
}

static void handle_line(int sock, const char *line) {
    if (!line || line[0] == '\0') {
        send_json(sock, "{\"ok\":false,\"error\":\"empty\"}");
        return;
    }
    if (strncmp(line, "PING", 4) == 0) {
        handle_ping(sock);
        return;
    }
    if (strstr(line, "MEAS") == line && strstr(line, "DIGITAL")) {
        handle_meas_digital(sock, line);
        return;
    }
    if (strstr(line, "MEAS") == line && strstr(line, "VOLT")) {
        handle_meas_voltage(sock, line);
        return;
    }
    if (strstr(line, "STIM") == line && strstr(line, "DIGITAL")) {
        handle_stim_digital(sock, line);
        return;
    }
    if (strstr(line, "SELFTEST") == line) {
        handle_selftest(sock, line);
        return;
    }
    send_json(sock, "{\"ok\":false,\"error\":\"unknown_command\"}");
}

static void tcp_server_task(void *arg) {
    (void)arg;
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(WIFI_PORT);
    addr.sin_addr.s_addr = htonl(INADDR_ANY);

    int listen_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
    if (listen_fd < 0) {
        ESP_LOGE(TAG, "socket failed");
        vTaskDelete(NULL);
        return;
    }
    int yes = 1;
    setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    if (bind(listen_fd, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
        ESP_LOGE(TAG, "bind failed");
        close(listen_fd);
        vTaskDelete(NULL);
        return;
    }
    if (listen(listen_fd, 2) != 0) {
        ESP_LOGE(TAG, "listen failed");
        close(listen_fd);
        vTaskDelete(NULL);
        return;
    }
    ESP_LOGI(TAG, "TCP server listening on port %d", WIFI_PORT);

    while (1) {
        struct sockaddr_in client = {0};
        socklen_t clen = sizeof(client);
        int sock = accept(listen_fd, (struct sockaddr *)&client, &clen);
        if (sock < 0) {
            continue;
        }
        send_json(sock, "{\"ok\":true,\"type\":\"hello\",\"fw\":\"v0.1\"}");
        char line[MAX_LINE];
        size_t pos = 0;
        while (1) {
            char c;
            int r = recv(sock, &c, 1, 0);
            if (r <= 0) {
                break;
            }
            if (c == '\r') {
                continue;
            }
            if (c == '\n') {
                line[pos] = '\0';
                handle_line(sock, line);
                pos = 0;
            } else if (pos + 1 < sizeof(line)) {
                line[pos++] = c;
            }
        }
        close(sock);
    }
}

void app_main(void) {
    esp_err_t nvs_ret = nvs_flash_init();
    if (nvs_ret == ESP_ERR_NVS_NO_FREE_PAGES || nvs_ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        nvs_ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(nvs_ret);

    gpio_init_defaults();
    adc_init();
    ESP_LOGI(TAG, "Delaying SoftAP startup for power stabilization");
    vTaskDelay(pdMS_TO_TICKS(3000));
    wifi_init_softap();

    xTaskCreate(tcp_server_task, "tcp_server", 4096, NULL, 5, NULL);
}
