CC=arm-none-eabi-gcc
OBJCOPY=arm-none-eabi-objcopy

BUILD_DIR ?= build
OUT_ELF ?= $(BUILD_DIR)/{SLUG}_app.elf
OUT_BIN ?= $(BUILD_DIR)/{SLUG}_app.bin

# PLACEHOLDER: adjust CUBE_ROOT to point to your STM32Cube SDK family
# For STM32F4: third_party/cache/STM32CubeF4
# For STM32F1: third_party/cache/STM32CubeF1
CUBE_ROOT = ../../../third_party/cache/PLACEHOLDER_STM32CubeFamily
CMSIS_CORE_INC = $(CUBE_ROOT)/Drivers/CMSIS/Include
CMSIS_DEV_INC = vendor/include/st

# PLACEHOLDER: set -mcpu and -DSTM32xxx for your MCU
# e.g. STM32F411: -mcpu=cortex-m4 -mthumb -DSTM32F411xE
# e.g. STM32F103: -mcpu=cortex-m3 -mthumb -DSTM32F103xB
CFLAGS = -mcpu=PLACEHOLDER_cpu -mthumb -O2 -ffreestanding \
         -fdata-sections -ffunction-sections -Wall -Wextra \
         -DPLACEHOLDER_MCU_DEFINE \
         -I$(CMSIS_CORE_INC) -I$(CMSIS_DEV_INC)

# PLACEHOLDER: replace with your MCU linker script
LDFLAGS = -T PLACEHOLDER_mcu.ld -Wl,--gc-sections -nostartfiles -nostdlib

SRCS = main.c vendor/st/system_PLACEHOLDER_stm32family.c
ASMSRCS = vendor/st/startup_PLACEHOLDER_stm32variant.s
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
