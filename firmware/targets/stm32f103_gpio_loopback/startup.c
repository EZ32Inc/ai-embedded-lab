void Reset_Handler(void);

__attribute__((section(".isr_vector")))
void (*const g_pfnVectors[])(void) = {
    (void (*)(void))0x20005000,
    Reset_Handler,
};

extern int main(void);

void Reset_Handler(void) {
    (void)main();
    while (1) {
    }
}
