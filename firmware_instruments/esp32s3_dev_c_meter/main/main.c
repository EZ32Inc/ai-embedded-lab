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

static void handle_meas_digital(int sock, const char *line) {
    int duration_ms = parse_int(find_kv(line, "DUR_MS"), 500);
    int samples[4] = {0};
    int ones[4] = {0};
    int zeros[4] = {0};
    int transitions[4] = {0};
    int last[4] = {-1, -1, -1, -1};
    int64_t start = esp_timer_get_time();
    int64_t end = start + ((int64_t)duration_ms * 1000);
    while (esp_timer_get_time() < end) {
        for (int i = 0; i < 4; i++) {
            int v = gpio_get_level(k_in_pins[i]);
            samples[i]++;
            if (v) {
                ones[i]++;
            } else {
                zeros[i]++;
            }
            if (last[i] >= 0 && v != last[i]) {
                transitions[i]++;
            }
            last[i] = v;
        }
    }
    char buf[512];
    int n = snprintf(buf, sizeof(buf), "{\"ok\":true,\"type\":\"digital\",\"duration_ms\":%d,\"pins\":[", duration_ms);
    for (int i = 0; i < 4; i++) {
        const char *state = "toggle";
        if (ones[i] == 0) {
            state = "low";
        } else if (zeros[i] == 0) {
            state = "high";
        }
        n += snprintf(
            buf + n,
            sizeof(buf) - n,
            "{\"gpio\":%d,\"state\":\"%s\",\"samples\":%d,\"ones\":%d,\"zeros\":%d,\"transitions\":%d}%s",
            k_in_pins[i],
            state,
            samples[i],
            ones[i],
            zeros[i],
            transitions[i],
            (i == 3) ? "" : ",");
    }
    snprintf(buf + n, sizeof(buf) - n, "]}");
    send_json(sock, buf);
}

static void handle_meas_voltage(int sock, const char *line) {
    int avg = parse_int(find_kv(line, "AVG"), 16);
    int total = 0;
    for (int i = 0; i < avg; i++) {
        int raw = 0;
        if (adc_oneshot_read(s_adc_handle, ADC_CHANNEL_3, &raw) == ESP_OK) {
            total += raw;
        }
    }
    int raw_avg = avg > 0 ? total / avg : 0;
    int mv = raw_avg;
    if (s_adc_cali) {
        adc_cali_raw_to_voltage(s_adc_cali, raw_avg, &mv);
    }
    float volts = ((float)mv) / 1000.0f;
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
    int duration_ms = parse_int(find_kv(line, "DUR_MS"), 200);
    int freq_hz = parse_int(find_kv(line, "FREQ_HZ"), 1000);

    if (!is_out_gpio(out_gpio) || !is_in_gpio(in_gpio)) {
        send_json(sock, "{\"ok\":false,\"error\":\"gpio_not_supported\"}");
        return;
    }

    gpio_set_direction(in_gpio, GPIO_MODE_INPUT);
    gpio_set_pull_mode(in_gpio, GPIO_FLOATING);
    gpio_set_direction(out_gpio, GPIO_MODE_OUTPUT);

    int period_us = freq_hz > 0 ? (1000000 / freq_hz) : 1000;
    if (period_us < 2) {
        period_us = 2;
    }

    int samples = 0;
    int ones = 0;
    int zeros = 0;
    int transitions = 0;
    int last = gpio_get_level(in_gpio);
    int level = 0;
    gpio_set_level(out_gpio, level);

    int64_t end = esp_timer_get_time() + ((int64_t)duration_ms * 1000);
    while (esp_timer_get_time() < end) {
        level = !level;
        gpio_set_level(out_gpio, level);
        esp_rom_delay_us(period_us / 2);

        int v = gpio_get_level(in_gpio);
        samples++;
        if (v) {
            ones++;
        } else {
            zeros++;
        }
        if (v != last) {
            transitions++;
        }
        last = v;
    }

    set_hiz(out_gpio);

    bool pass = transitions > 0 && ones > 0 && zeros > 0;
    char buf[256];
    snprintf(
        buf,
        sizeof(buf),
        "{\"ok\":true,\"type\":\"selftest\",\"out_gpio\":%d,\"in_gpio\":%d,\"duration_ms\":%d,"
        "\"samples\":%d,\"ones\":%d,\"zeros\":%d,\"transitions\":%d,\"pass\":%s}",
        out_gpio,
        in_gpio,
        duration_ms,
        samples,
        ones,
        zeros,
        transitions,
        pass ? "true" : "false");
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
    wifi_init_softap();

    xTaskCreate(tcp_server_task, "tcp_server", 4096, NULL, 5, NULL);
}
