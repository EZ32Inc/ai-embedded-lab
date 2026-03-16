CC      = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
NM      = arm-none-eabi-nm

BUILD_DIR ?= build
OUT_ELF   ?= $(BUILD_DIR)/stm32h750_minimal_runtime_mailbox_app.elf
OUT_BIN   ?= $(BUILD_DIR)/stm32h750_minimal_runtime_mailbox_app.bin

LDSCRIPT = stm32h750.ld

# Cortex-M7 with FPU (H750 has FPv5-D16)
CFLAGS  = -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard \
          -O2 -ffreestanding -fdata-sections -ffunction-sections \
          -Wall -Wextra -nostdlib
LDFLAGS = -T $(LDSCRIPT) -Wl,--gc-sections -nostdlib

OBJS = $(BUILD_DIR)/main.o $(BUILD_DIR)/startup.o

all: $(OUT_ELF) $(OUT_BIN) nm-check

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

# Verify .bss does not overlap mailbox address (0x38000000)
nm-check: $(OUT_ELF)
	@echo "--- nm check: .bss and stack layout ---"
	@$(NM) $< | grep -E "_ebss|_sbss|_estack|_sdata|_edata" | sort -k1
	@echo "--- mailbox provisional address: 0x38000000 (SRAM4) ---"
	@echo "--- confirm _ebss is well below 0x38000000          ---"

clean:
	rm -rf $(BUILD_DIR)
