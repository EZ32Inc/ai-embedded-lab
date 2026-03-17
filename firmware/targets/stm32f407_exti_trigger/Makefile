CC      = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy

BUILD_DIR ?= build
OUT_ELF   ?= $(BUILD_DIR)/stm32f407_exti_trigger_app.elf
OUT_BIN   ?= $(BUILD_DIR)/stm32f407_exti_trigger_app.bin

BASE     = ../stm32f407_discovery
CUBE_ROOT    = ../../../third_party/cache/STM32CubeF4
CMSIS_CORE_INC = $(CUBE_ROOT)/Drivers/CMSIS/Include
CMSIS_DEV_INC  = $(BASE)/vendor/include/st

CFLAGS  = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
          -O0 -g3 \
          -ffreestanding -fdata-sections -ffunction-sections \
          -Wall -Wextra \
          -DSTM32F407xx \
          -I$(CMSIS_CORE_INC) -I$(CMSIS_DEV_INC) -I$(BASE)

LDFLAGS = -T $(BASE)/stm32f407.ld -Wl,--gc-sections -nostartfiles -nostdlib \
          -Wl,--defsym=__libc_init_array=0

OBJS = $(BUILD_DIR)/main.o \
       $(BUILD_DIR)/system.o \
       $(BUILD_DIR)/startup.o

all: $(OUT_ELF) $(OUT_BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/main.o: main.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/system.o: $(BASE)/vendor/st/system_stm32f4xx.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/startup.o: $(BASE)/vendor/st/startup_stm32f407xx.s | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT_ELF): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $@ $(LDFLAGS) -lgcc

$(OUT_BIN): $(OUT_ELF)
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD_DIR)
