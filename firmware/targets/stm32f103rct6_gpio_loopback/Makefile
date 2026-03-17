CC      = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy

BUILD_DIR ?= build
OUT_ELF   ?= $(BUILD_DIR)/stm32f103rct6_gpio_loopback_app.elf
OUT_BIN   ?= $(BUILD_DIR)/stm32f103rct6_gpio_loopback_app.bin

BASE = ../stm32f103rct6

CFLAGS  = -mcpu=cortex-m3 -mthumb \
          -O0 -g3 \
          -ffreestanding -fdata-sections -ffunction-sections \
          -Wall -Wextra \
          -I$(BASE)

LDFLAGS = -T $(BASE)/stm32f103rct6.ld -Wl,--gc-sections -nostartfiles -nostdlib

OBJS = $(BUILD_DIR)/main.o $(BUILD_DIR)/startup.o

all: $(OUT_ELF) $(OUT_BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/main.o: main.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/startup.o: $(BASE)/startup_stm32f103.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT_ELF): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $@ $(LDFLAGS) -lgcc

$(OUT_BIN): $(OUT_ELF)
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD_DIR)
