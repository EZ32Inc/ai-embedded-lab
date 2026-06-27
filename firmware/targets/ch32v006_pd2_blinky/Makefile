TARGET    = ch32v006_pd2_blinky
TOOLCHAIN = /nvme1t/wch-riscv-gcc/bin
WCH_EVT   = /nvme1t/github/CH32V006/EVT/EXAM

GCC      = $(TOOLCHAIN)/riscv-none-embed-gcc
OBJCOPY  = $(TOOLCHAIN)/riscv-none-embed-objcopy

OUT_ELF ?= $(TARGET).elf
OUT_BIN ?= $(TARGET).bin

ARCH_FLAGS = -march=rv32ec -mabi=ilp32e
INCLUDES = -I. \
           -I$(WCH_EVT)/SRC/Core \
           -I$(WCH_EVT)/SRC/Debug \
           -I$(WCH_EVT)/SRC/Peripheral/inc

CFLAGS = $(ARCH_FLAGS) \
         -O2 -g \
         -nostdlib \
         -ffunction-sections -fdata-sections \
         -DCH32V006 \
         -DHSE_VALUE=12000000 \
         $(INCLUDES) \
         -Wall

LDFLAGS = $(ARCH_FLAGS) \
          -T ch32v006.ld \
          -nostdlib \
          -Wl,--gc-sections \
          -Wl,-Map=$(TARGET).map

SRCS = main.c \
       system_ch32v00X.c \
       $(WCH_EVT)/SRC/Startup/startup_ch32v00X.S \
       $(WCH_EVT)/SRC/Core/core_riscv.c \
       $(WCH_EVT)/SRC/Debug/debug.c \
       $(WCH_EVT)/SRC/Peripheral/src/ch32v00X_gpio.c \
       $(WCH_EVT)/SRC/Peripheral/src/ch32v00X_rcc.c \
       $(WCH_EVT)/SRC/Peripheral/src/ch32v00X_misc.c \
       $(WCH_EVT)/SRC/Peripheral/src/ch32v00X_usart.c

OBJS = $(notdir $(SRCS:=.o))

all: $(OUT_ELF) $(OUT_BIN)

$(OUT_ELF): $(OBJS)
	$(GCC) $(LDFLAGS) -o $@ $^ -lgcc

%.c.o: %.c
	$(GCC) $(CFLAGS) -c -o $@ $<

%.S.o: %.S
	$(GCC) $(CFLAGS) -c -o $@ $<

startup_ch32v00X.S.o: $(WCH_EVT)/SRC/Startup/startup_ch32v00X.S
	$(GCC) $(CFLAGS) -c -o $@ $<

core_riscv.c.o: $(WCH_EVT)/SRC/Core/core_riscv.c
	$(GCC) $(CFLAGS) -c -o $@ $<

debug.c.o: $(WCH_EVT)/SRC/Debug/debug.c
	$(GCC) $(CFLAGS) -c -o $@ $<

ch32v00X_gpio.c.o: $(WCH_EVT)/SRC/Peripheral/src/ch32v00X_gpio.c
	$(GCC) $(CFLAGS) -c -o $@ $<

ch32v00X_rcc.c.o: $(WCH_EVT)/SRC/Peripheral/src/ch32v00X_rcc.c
	$(GCC) $(CFLAGS) -c -o $@ $<

ch32v00X_misc.c.o: $(WCH_EVT)/SRC/Peripheral/src/ch32v00X_misc.c
	$(GCC) $(CFLAGS) -c -o $@ $<

ch32v00X_usart.c.o: $(WCH_EVT)/SRC/Peripheral/src/ch32v00X_usart.c
	$(GCC) $(CFLAGS) -c -o $@ $<

$(OUT_BIN): $(OUT_ELF)
	$(OBJCOPY) -O binary $< $@

clean:
	rm -f *.o $(TARGET).elf $(TARGET).bin $(TARGET).map $(OUT_ELF) $(OUT_BIN)

.PHONY: all clean
