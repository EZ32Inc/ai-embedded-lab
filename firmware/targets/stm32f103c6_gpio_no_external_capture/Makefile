CC=arm-none-eabi-gcc
OBJCOPY=arm-none-eabi-objcopy

BUILD_DIR ?= build
OUT_ELF ?= $(BUILD_DIR)/stm32f103c6_gpio_no_external_capture_app.elf
OUT_BIN ?= $(BUILD_DIR)/stm32f103c6_gpio_no_external_capture_app.bin

CFLAGS = -mcpu=cortex-m3 -mthumb -O2 -ffreestanding -fdata-sections -ffunction-sections -Wall -Wextra -nostdlib
LDFLAGS = -T stm32f103c6.ld -Wl,--gc-sections -nostdlib

MAIN_SRC = ../stm32f103_gpio_no_external_capture/main.c
STARTUP_SRC = startup.c
MAIN_OBJ = $(BUILD_DIR)/main.o
STARTUP_OBJ = $(BUILD_DIR)/startup.o

all: $(OUT_ELF) $(OUT_BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(MAIN_OBJ): $(MAIN_SRC) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(STARTUP_OBJ): $(STARTUP_SRC) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT_ELF): $(STARTUP_OBJ) $(MAIN_OBJ)
	$(CC) $(CFLAGS) $(STARTUP_OBJ) $(MAIN_OBJ) -o $@ $(LDFLAGS)

$(OUT_BIN): $(OUT_ELF)
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD_DIR)
