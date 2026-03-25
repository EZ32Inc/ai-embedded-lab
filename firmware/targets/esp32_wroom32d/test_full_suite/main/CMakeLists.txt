idf_component_register(SRCS "main.c" INCLUDE_DIRS "."
                        REQUIRES ael_board nvs_flash esp_wifi bt
                                 esp_driver_pcnt esp_driver_i2c esp_adc)
