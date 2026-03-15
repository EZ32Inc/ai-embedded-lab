cmake_minimum_required(VERSION 3.13)

# PLACEHOLDER: copy pico_sdk_import.cmake from an existing rp target
# (e.g. firmware/targets/rp2040_pico/pico_sdk_import.cmake)
include(pico_sdk_import.cmake)

project({SLUG} C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable({SLUG}
    main.c
)

target_link_libraries({SLUG} pico_stdlib)

pico_enable_stdio_usb({SLUG} 0)
pico_enable_stdio_uart({SLUG} 0)

pico_add_extra_outputs({SLUG})
