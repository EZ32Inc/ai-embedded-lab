extern int main(void);

extern unsigned long _etext;
extern unsigned long _sdata;
extern unsigned long _edata;
extern unsigned long _sbss;
extern unsigned long _ebss;

void reset_handler(void);
void default_handler(void);

void nmi_handler(void) __attribute__((weak, alias("default_handler")));
void hardfault_handler(void) __attribute__((weak, alias("default_handler")));

__attribute__((section(".isr_vector")))
void (*const vector_table[])(void) = {
    (void (*)(void))0x20005000,
    reset_handler,
    nmi_handler,
    hardfault_handler,
};

void reset_handler(void) {
    unsigned long *src = &_etext;
    unsigned long *dst = &_sdata;
    while (dst < &_edata) {
        *dst++ = *src++;
    }
    for (dst = &_sbss; dst < &_ebss; dst++) {
        *dst = 0;
    }
    (void)main();
    while (1) {
    }
}

void default_handler(void) {
    while (1) {
    }
}
