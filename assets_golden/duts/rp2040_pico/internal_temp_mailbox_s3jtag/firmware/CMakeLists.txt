cmake_minimum_required(VERSION 3.13)

include(pico_sdk_import.cmake)

project(pico_internal_temp_mailbox_s3jtag C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(pico_internal_temp_mailbox_s3jtag
    main.c
)

target_link_libraries(pico_internal_temp_mailbox_s3jtag pico_stdlib hardware_adc)

pico_enable_stdio_usb(pico_internal_temp_mailbox_s3jtag 0)
pico_enable_stdio_uart(pico_internal_temp_mailbox_s3jtag 0)

pico_add_extra_outputs(pico_internal_temp_mailbox_s3jtag)
