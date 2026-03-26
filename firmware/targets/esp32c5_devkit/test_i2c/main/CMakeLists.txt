idf_component_register(SRCS "main.c" INCLUDE_DIRS "."
                        REQUIRES driver nvs_flash esp_timer freertos esp_driver_i2c)
