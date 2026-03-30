#include <stdint.h>

extern int main(void);

extern uint32_t _estack;
extern uint32_t _etext;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

void Reset_Handler(void);
void Default_Handler(void);
void TIM3_IRQHandler(void);

/*
 * STM32G431 vector table — RM0440 Table 83.
 * Core exceptions (first 16) + vendor IRQs 0-29 (just enough for TIM3=IRQ29).
 */
__attribute__((section(".isr_vector")))
void (*const vector_table[])(void) = {
    (void (*)(void))(&_estack),
    Reset_Handler,   /* Reset */
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
    Default_Handler, /* IRQ0  WWDG */
    Default_Handler, /* IRQ1  PVD/PVM1 */
    Default_Handler, /* IRQ2  RTC_TAMP_LSECSS */
    Default_Handler, /* IRQ3  RTC_WKUP */
    Default_Handler, /* IRQ4  FLASH */
    Default_Handler, /* IRQ5  RCC */
    Default_Handler, /* IRQ6  EXTI0 */
    Default_Handler, /* IRQ7  EXTI1 */
    Default_Handler, /* IRQ8  EXTI2 */
    Default_Handler, /* IRQ9  EXTI3 */
    Default_Handler, /* IRQ10 EXTI4 */
    Default_Handler, /* IRQ11 DMA1_CH1 */
    Default_Handler, /* IRQ12 DMA1_CH2 */
    Default_Handler, /* IRQ13 DMA1_CH3 */
    Default_Handler, /* IRQ14 DMA1_CH4 */
    Default_Handler, /* IRQ15 DMA1_CH5 */
    Default_Handler, /* IRQ16 DMA1_CH6 */
    Default_Handler, /* IRQ17 DMA1_CH7 */
    Default_Handler, /* IRQ18 ADC1_2 */
    Default_Handler, /* IRQ19 USB_HP or CAN1_TX */
    Default_Handler, /* IRQ20 USB_LP or CAN1_RX0 */
    Default_Handler, /* IRQ21 fdCAN1_IT1 */
    Default_Handler, /* IRQ22 fdCAN1_IT0 */
    Default_Handler, /* IRQ23 EXTI9_5 */
    Default_Handler, /* IRQ24 TIM1_BRK_TIM15 */
    Default_Handler, /* IRQ25 TIM1_UP_TIM16 */
    Default_Handler, /* IRQ26 TIM1_TRG_COM_TIM17 */
    Default_Handler, /* IRQ27 TIM1_CC */
    Default_Handler, /* IRQ28 TIM2 */
    TIM3_IRQHandler, /* IRQ29 TIM3 */
};

void Reset_Handler(void) {
    uint32_t *src = &_etext;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) {
        *dst++ = *src++;
    }
    dst = &_sbss;
    while (dst < &_ebss) {
        *dst++ = 0;
    }

    (void)main();
    while (1) {}
}

void Default_Handler(void) {
    while (1) {}
}
