cmake_minimum_required(VERSION 3.13)

include(pico_sdk_import.cmake)

project(pico_i2c_banner C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(pico_i2c_banner
    main.c
)

target_link_libraries(pico_i2c_banner pico_stdlib hardware_i2c)

pico_enable_stdio_usb(pico_i2c_banner 1)
pico_enable_stdio_uart(pico_i2c_banner 0)

pico_add_extra_outputs(pico_i2c_banner)
