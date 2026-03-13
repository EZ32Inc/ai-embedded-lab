extern int main(void);

void reset_handler(void) {
    main();
    while (1) {
    }
}

void default_handler(void) {
    while (1) {
    }
}

__attribute__((section(".isr_vector")))
void (*const g_vectors[])(void) = {
    (void (*)(void))0x20005000,
    reset_handler,
    default_handler,
    default_handler,
    default_handler,
    default_handler,
    default_handler,
    0,
    0,
    0,
    0,
    default_handler,
    default_handler,
    0,
    default_handler,
    default_handler,
};
