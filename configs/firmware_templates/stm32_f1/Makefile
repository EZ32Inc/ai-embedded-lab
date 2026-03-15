CC=arm-none-eabi-gcc
OBJCOPY=arm-none-eabi-objcopy

BUILD_DIR ?= build
OUT_ELF ?= $(BUILD_DIR)/{SLUG}_app.elf
OUT_BIN ?= $(BUILD_DIR)/{SLUG}_app.bin

# STM32F1 family — uses STM32CubeF1
CUBE_ROOT = ../../../third_party/cache/STM32CubeF1
CMSIS_CORE_INC = $(CUBE_ROOT)/Drivers/CMSIS/Include
CMSIS_DEV_INC = vendor/include/st

# Cortex-M3 (no FPU)
# PLACEHOLDER: add the exact MCU variant define, e.g. -DSTM32F103xB or -DSTM32F103xE
CFLAGS = -mcpu=cortex-m3 -mthumb \
         -O2 -ffreestanding \
         -fdata-sections -ffunction-sections -Wall -Wextra \
         -DPLACEHOLDER_MCU_VARIANT \
         -I$(CMSIS_CORE_INC) -I$(CMSIS_DEV_INC)

# PLACEHOLDER: replace with your MCU linker script (e.g. stm32f103c8.ld)
LDFLAGS = -T PLACEHOLDER_mcu.ld -Wl,--gc-sections -nostartfiles -nostdlib

SRCS = main.c vendor/st/system_stm32f1xx.c
ASMSRCS = vendor/st/startup_PLACEHOLDER_stm32f1variant.s
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
