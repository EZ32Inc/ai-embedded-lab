MEMORY
{
  FLASH (rx)    : ORIGIN = 0x08000000, LENGTH = 512K
  RAM (rwx)     : ORIGIN = 0x20000000, LENGTH = 63K
  MAILBOX (rwx) : ORIGIN = 0x2000FC00, LENGTH = 1K
}

_estack = ORIGIN(MAILBOX);
__ael_mailbox_start__ = ORIGIN(MAILBOX);

SECTIONS
{
  .isr_vector :
  {
    KEEP(*(.isr_vector))
  } > FLASH

  .text :
  {
    *(.text*)
    *(.rodata*)
    _etext = .;
  } > FLASH

  .data :
  {
    _sidata = LOADADDR(.data);
    _sdata = .;
    *(.data*)
    _edata = .;
  } > RAM

  .bss :
  {
    _sbss = .;
    *(.bss*)
    *(COMMON)
    _ebss = .;
  } > RAM

  .ael_mailbox (NOLOAD) :
  {
    . = ORIGIN(MAILBOX);
    . += LENGTH(MAILBOX);
  } > MAILBOX
}
