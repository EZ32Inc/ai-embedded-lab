cmake_minimum_required(VERSION 3.13)

include(pico_sdk_import.cmake)

project(pico_blink C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(pico_blink
    main.c
)

target_link_libraries(pico_blink pico_stdlib)

pico_enable_stdio_usb(pico_blink 0)
pico_enable_stdio_uart(pico_blink 0)

pico_add_extra_outputs(pico_blink)
