cmake_minimum_required(VERSION 3.13)

set(PICO_BOARD pico2 CACHE STRING "Board type")

include(pico_sdk_import.cmake)

project(pico2_uart_banner C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(pico2_uart_banner
    main.c
)

target_link_libraries(pico2_uart_banner pico_stdlib)

pico_enable_stdio_usb(pico2_uart_banner 1)
pico_enable_stdio_uart(pico2_uart_banner 0)

pico_add_extra_outputs(pico2_uart_banner)
