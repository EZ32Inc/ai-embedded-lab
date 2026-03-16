CC=arm-none-eabi-gcc
OBJCOPY=arm-none-eabi-objcopy

BUILD_DIR ?= build
OUT_ELF ?= $(BUILD_DIR)/stm32g431_spi_app.elf
OUT_BIN ?= $(BUILD_DIR)/stm32g431_spi_app.bin

STARTUP_SRC = ../stm32g431cbu6/startup.c
LDSCRIPT    = ../stm32g431cbu6/stm32g431.ld

CFLAGS = -mcpu=cortex-m4 -mthumb -O2 -ffreestanding -fdata-sections -ffunction-sections -Wall -Wextra -nostdlib
LDFLAGS = -T $(LDSCRIPT) -Wl,--gc-sections -nostdlib

OBJS = $(BUILD_DIR)/main.o $(BUILD_DIR)/startup.o

all: $(OUT_ELF) $(OUT_BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/main.o: main.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/startup.o: $(STARTUP_SRC) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT_ELF): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $@ $(LDFLAGS)

$(OUT_BIN): $(OUT_ELF)
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD_DIR)
