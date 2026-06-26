CC      = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy

BUILD_DIR ?= build
OUT_ELF   ?= $(BUILD_DIR)/stm32h503_pc13_blinky.elf
OUT_BIN   ?= $(BUILD_DIR)/stm32h503_pc13_blinky.bin

CFLAGS  = -mcpu=cortex-m33 -mthumb -O2 -ffreestanding -fdata-sections -ffunction-sections -Wall -Wextra -nostdlib
LDFLAGS = -T stm32h503.ld -Wl,--gc-sections -nostdlib

OBJS = $(BUILD_DIR)/main.o $(BUILD_DIR)/startup.o

.PHONY: all clean

all: $(OUT_ELF) $(OUT_BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/main.o: main.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/startup.o: startup.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT_ELF): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $@ $(LDFLAGS)

$(OUT_BIN): $(OUT_ELF)
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD_DIR)
