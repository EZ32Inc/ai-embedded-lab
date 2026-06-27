CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy

BUILD_DIR ?= build
OUT_ELF ?= $(BUILD_DIR)/stm32f401_blackpill_pc13_blinky.elf
OUT_BIN ?= $(BUILD_DIR)/stm32f401_blackpill_pc13_blinky.bin

CUBE_ROOT = ../../../third_party/cache/STM32CubeF4
CMSIS_CORE_INC = $(CUBE_ROOT)/Drivers/CMSIS/Include
CMSIS_DEV_INC = ../stm32f401ce/vendor/include/st
SYSTEM_SRC = ../stm32f401ce/vendor/st/system_stm32f4xx.c
STARTUP_SRC = ../stm32f401ce/vendor/st/startup_stm32f401xe.s

CFLAGS = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
         -O2 -ffreestanding \
         -fdata-sections -ffunction-sections -Wall -Wextra \
         -DSTM32F401xE \
         -I$(CMSIS_CORE_INC) -I$(CMSIS_DEV_INC)

LDFLAGS = -T stm32f401_blackpill.ld -Wl,--gc-sections -nostartfiles -nostdlib

OBJS = $(BUILD_DIR)/main.o \
       $(BUILD_DIR)/system_stm32f4xx.o \
       $(BUILD_DIR)/startup_stm32f401xe.o

all: $(OUT_ELF) $(OUT_BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/main.o: main.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/system_stm32f4xx.o: $(SYSTEM_SRC) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/startup_stm32f401xe.o: $(STARTUP_SRC) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT_ELF): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $@ $(LDFLAGS) -lgcc

$(OUT_BIN): $(OUT_ELF)
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD_DIR)

.PHONY: all clean
