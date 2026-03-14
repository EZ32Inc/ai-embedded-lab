CC=arm-none-eabi-gcc
OBJCOPY=arm-none-eabi-objcopy

BUILD_DIR ?= build
OUT_ELF ?= $(BUILD_DIR)/stm32f411_app.elf
OUT_BIN ?= $(BUILD_DIR)/stm32f411_app.bin

CUBE_ROOT = ../../../third_party/cache/STM32CubeF4
CMSIS_CORE_INC = $(CUBE_ROOT)/Drivers/CMSIS/Include
CMSIS_DEV_INC = vendor/include/st

CFLAGS = -mcpu=cortex-m4 -mthumb -O2 -ffreestanding -fdata-sections -ffunction-sections -Wall -Wextra -DSTM32F411xE -I$(CMSIS_CORE_INC) -I$(CMSIS_DEV_INC)
LDFLAGS = -T stm32f411.ld -Wl,--gc-sections -nostartfiles -nostdlib

SRCS = main.c vendor/st/system_stm32f4xx.c
ASMSRCS = vendor/st/startup_stm32f411xe.s
OBJS = $(SRCS:%.c=$(BUILD_DIR)/%.o) $(ASMSRCS:%.s=$(BUILD_DIR)/%.o)

all: $(OUT_ELF) $(OUT_BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)/vendor/st

$(BUILD_DIR)/%.o: %.c | $(BUILD_DIR)
	mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/%.o: %.s | $(BUILD_DIR)
	mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT_ELF): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $@ $(LDFLAGS) -lgcc

$(OUT_BIN): $(OUT_ELF)
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD_DIR)
