idf_component_register(SRCS "main.c" INCLUDE_DIRS "."
                        REQUIRES ael_board nvs_flash esp_wifi bt driver esp_driver_pcnt esp_adc esp_driver_i2c)
