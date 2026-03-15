CC=arm-none-eabi-gcc
OBJCOPY=arm-none-eabi-objcopy

BUILD_DIR ?= build
OUT_ELF ?= $(BUILD_DIR)/{SLUG}_app.elf
OUT_BIN ?= $(BUILD_DIR)/{SLUG}_app.bin

# STM32F4 family — uses STM32CubeF4
CUBE_ROOT = ../../../third_party/cache/STM32CubeF4
CMSIS_CORE_INC = $(CUBE_ROOT)/Drivers/CMSIS/Include
CMSIS_DEV_INC = vendor/include/st

# Cortex-M4 with FPU (hard-float ABI)
# PLACEHOLDER: add the exact MCU variant define, e.g. -DSTM32F407xx or -DSTM32F401xE
CFLAGS = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
         -O2 -ffreestanding \
         -fdata-sections -ffunction-sections -Wall -Wextra \
         -DPLACEHOLDER_MCU_VARIANT \
         -I$(CMSIS_CORE_INC) -I$(CMSIS_DEV_INC)

# PLACEHOLDER: replace with your MCU linker script (e.g. stm32f407vg.ld, stm32f401re.ld)
LDFLAGS = -T PLACEHOLDER_mcu.ld -Wl,--gc-sections -nostartfiles -nostdlib

SRCS = main.c vendor/st/system_stm32f4xx.c
ASMSRCS = vendor/st/startup_PLACEHOLDER_stm32f4variant.s
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
