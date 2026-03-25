idf_component_register(SRCS "main.c" INCLUDE_DIRS "."
                        REQUIRES driver esp_wifi esp_netif bt nvs_flash
                                 esp_timer freertos esp_adc
                                 esp_driver_pcnt esp_driver_i2c)
