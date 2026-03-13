void Reset_Handler(void);
void Default_Handler(void);
void EXTI9_5_IRQHandler(void);

__attribute__((section(".isr_vector")))
void (*const g_pfnVectors[])(void) = {
    (void (*)(void))0x20005000,
    Reset_Handler,
    Default_Handler, /* NMI */
    Default_Handler, /* HardFault */
    Default_Handler, /* MemManage */
    Default_Handler, /* BusFault */
    Default_Handler, /* UsageFault */
    0,
    0,
    0,
    0,
    Default_Handler, /* SVCall */
    Default_Handler, /* DebugMon */
    0,
    Default_Handler, /* PendSV */
    Default_Handler, /* SysTick */
    Default_Handler, /* IRQ0  */
    Default_Handler, /* IRQ1  */
    Default_Handler, /* IRQ2  */
    Default_Handler, /* IRQ3  */
    Default_Handler, /* IRQ4  */
    Default_Handler, /* IRQ5  */
    Default_Handler, /* IRQ6  */
    Default_Handler, /* IRQ7  */
    Default_Handler, /* IRQ8  */
    Default_Handler, /* IRQ9  */
    Default_Handler, /* IRQ10 */
    Default_Handler, /* IRQ11 */
    Default_Handler, /* IRQ12 */
    Default_Handler, /* IRQ13 */
    Default_Handler, /* IRQ14 */
    Default_Handler, /* IRQ15 */
    Default_Handler, /* IRQ16 */
    Default_Handler, /* IRQ17 */
    Default_Handler, /* IRQ18 */
    Default_Handler, /* IRQ19 */
    Default_Handler, /* IRQ20 */
    Default_Handler, /* IRQ21 */
    Default_Handler, /* IRQ22 */
    EXTI9_5_IRQHandler, /* IRQ23 */
};

extern int main(void);

void Reset_Handler(void) {
    (void)main();
    while (1) {
    }
}

void Default_Handler(void) {
    while (1) {
    }
}
