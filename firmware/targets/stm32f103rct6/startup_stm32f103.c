/*
 * Minimal Cortex-M3 startup for STM32F103RCT6
 * Full vector table: 16 core exceptions + 60 external IRQs
 */
#include <stdint.h>

extern int main(void);
extern uint32_t _estack;
extern uint32_t _sidata;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

void Reset_Handler(void);
void Default_Handler(void);

/* Weak aliases — test firmware overrides what it needs */
void NMI_Handler(void)          __attribute__((weak, alias("Default_Handler")));
void HardFault_Handler(void)    __attribute__((weak, alias("Default_Handler")));
void MemManage_Handler(void)    __attribute__((weak, alias("Default_Handler")));
void BusFault_Handler(void)     __attribute__((weak, alias("Default_Handler")));
void UsageFault_Handler(void)   __attribute__((weak, alias("Default_Handler")));
void SVC_Handler(void)          __attribute__((weak, alias("Default_Handler")));
void DebugMon_Handler(void)     __attribute__((weak, alias("Default_Handler")));
void PendSV_Handler(void)       __attribute__((weak, alias("Default_Handler")));
void SysTick_Handler(void)      __attribute__((weak, alias("Default_Handler")));

/* External IRQs (weak — test firmware overrides needed handlers) */
void WWDG_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void PVD_IRQHandler(void)            __attribute__((weak, alias("Default_Handler")));
void TAMPER_IRQHandler(void)         __attribute__((weak, alias("Default_Handler")));
void RTC_IRQHandler(void)            __attribute__((weak, alias("Default_Handler")));
void FLASH_IRQHandler(void)          __attribute__((weak, alias("Default_Handler")));
void RCC_IRQHandler(void)            __attribute__((weak, alias("Default_Handler")));
void EXTI0_IRQHandler(void)          __attribute__((weak, alias("Default_Handler")));
void EXTI1_IRQHandler(void)          __attribute__((weak, alias("Default_Handler")));
void EXTI2_IRQHandler(void)          __attribute__((weak, alias("Default_Handler")));
void EXTI3_IRQHandler(void)          __attribute__((weak, alias("Default_Handler")));
void EXTI4_IRQHandler(void)          __attribute__((weak, alias("Default_Handler")));
void DMA1_Channel1_IRQHandler(void)  __attribute__((weak, alias("Default_Handler")));
void DMA1_Channel2_IRQHandler(void)  __attribute__((weak, alias("Default_Handler")));
void DMA1_Channel3_IRQHandler(void)  __attribute__((weak, alias("Default_Handler")));
void DMA1_Channel4_IRQHandler(void)  __attribute__((weak, alias("Default_Handler")));
void DMA1_Channel5_IRQHandler(void)  __attribute__((weak, alias("Default_Handler")));
void DMA1_Channel6_IRQHandler(void)  __attribute__((weak, alias("Default_Handler")));
void DMA1_Channel7_IRQHandler(void)  __attribute__((weak, alias("Default_Handler")));
void ADC1_2_IRQHandler(void)         __attribute__((weak, alias("Default_Handler")));
void USB_HP_CAN1_TX_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void USB_LP_CAN1_RX0_IRQHandler(void)__attribute__((weak, alias("Default_Handler")));
void CAN1_RX1_IRQHandler(void)       __attribute__((weak, alias("Default_Handler")));
void CAN1_SCE_IRQHandler(void)       __attribute__((weak, alias("Default_Handler")));
void EXTI9_5_IRQHandler(void)        __attribute__((weak, alias("Default_Handler")));
void TIM1_BRK_IRQHandler(void)       __attribute__((weak, alias("Default_Handler")));
void TIM1_UP_IRQHandler(void)        __attribute__((weak, alias("Default_Handler")));
void TIM1_TRG_COM_IRQHandler(void)   __attribute__((weak, alias("Default_Handler")));
void TIM1_CC_IRQHandler(void)        __attribute__((weak, alias("Default_Handler")));
void TIM2_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void TIM3_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void TIM4_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void I2C1_EV_IRQHandler(void)        __attribute__((weak, alias("Default_Handler")));
void I2C1_ER_IRQHandler(void)        __attribute__((weak, alias("Default_Handler")));
void I2C2_EV_IRQHandler(void)        __attribute__((weak, alias("Default_Handler")));
void I2C2_ER_IRQHandler(void)        __attribute__((weak, alias("Default_Handler")));
void SPI1_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void SPI2_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void USART1_IRQHandler(void)         __attribute__((weak, alias("Default_Handler")));
void USART2_IRQHandler(void)         __attribute__((weak, alias("Default_Handler")));
void USART3_IRQHandler(void)         __attribute__((weak, alias("Default_Handler")));
void EXTI15_10_IRQHandler(void)      __attribute__((weak, alias("Default_Handler")));
void RTC_Alarm_IRQHandler(void)      __attribute__((weak, alias("Default_Handler")));
void USBWakeUp_IRQHandler(void)      __attribute__((weak, alias("Default_Handler")));
void TIM8_BRK_IRQHandler(void)       __attribute__((weak, alias("Default_Handler")));
void TIM8_UP_IRQHandler(void)        __attribute__((weak, alias("Default_Handler")));
void TIM8_TRG_COM_IRQHandler(void)   __attribute__((weak, alias("Default_Handler")));
void TIM8_CC_IRQHandler(void)        __attribute__((weak, alias("Default_Handler")));
void ADC3_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void FSMC_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void SDIO_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void TIM5_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void SPI3_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void UART4_IRQHandler(void)          __attribute__((weak, alias("Default_Handler")));
void UART5_IRQHandler(void)          __attribute__((weak, alias("Default_Handler")));
void TIM6_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void TIM7_IRQHandler(void)           __attribute__((weak, alias("Default_Handler")));
void DMA2_Channel1_IRQHandler(void)  __attribute__((weak, alias("Default_Handler")));
void DMA2_Channel2_IRQHandler(void)  __attribute__((weak, alias("Default_Handler")));
void DMA2_Channel3_IRQHandler(void)  __attribute__((weak, alias("Default_Handler")));
void DMA2_Channel4_5_IRQHandler(void)__attribute__((weak, alias("Default_Handler")));

__attribute__((section(".isr_vector")))
void (*const vector_table[])(void) = {
    /* Core exceptions */
    (void (*)(void))(&_estack),   /* Initial stack pointer */
    Reset_Handler,                /* Reset */
    NMI_Handler,
    HardFault_Handler,
    MemManage_Handler,
    BusFault_Handler,
    UsageFault_Handler,
    0, 0, 0, 0,                   /* Reserved */
    SVC_Handler,
    DebugMon_Handler,
    0,                            /* Reserved */
    PendSV_Handler,
    SysTick_Handler,
    /* External IRQs (position 0-59) */
    WWDG_IRQHandler,              /* 0 */
    PVD_IRQHandler,               /* 1 */
    TAMPER_IRQHandler,            /* 2 */
    RTC_IRQHandler,               /* 3 */
    FLASH_IRQHandler,             /* 4 */
    RCC_IRQHandler,               /* 5 */
    EXTI0_IRQHandler,             /* 6 */
    EXTI1_IRQHandler,             /* 7 */
    EXTI2_IRQHandler,             /* 8 */
    EXTI3_IRQHandler,             /* 9 */
    EXTI4_IRQHandler,             /* 10 */
    DMA1_Channel1_IRQHandler,     /* 11 */
    DMA1_Channel2_IRQHandler,     /* 12 */
    DMA1_Channel3_IRQHandler,     /* 13 */
    DMA1_Channel4_IRQHandler,     /* 14 */
    DMA1_Channel5_IRQHandler,     /* 15 */
    DMA1_Channel6_IRQHandler,     /* 16 */
    DMA1_Channel7_IRQHandler,     /* 17 */
    ADC1_2_IRQHandler,            /* 18 */
    USB_HP_CAN1_TX_IRQHandler,    /* 19 */
    USB_LP_CAN1_RX0_IRQHandler,   /* 20 */
    CAN1_RX1_IRQHandler,          /* 21 */
    CAN1_SCE_IRQHandler,          /* 22 */
    EXTI9_5_IRQHandler,           /* 23 */
    TIM1_BRK_IRQHandler,          /* 24 */
    TIM1_UP_IRQHandler,           /* 25 */
    TIM1_TRG_COM_IRQHandler,      /* 26 */
    TIM1_CC_IRQHandler,           /* 27 */
    TIM2_IRQHandler,              /* 28 */
    TIM3_IRQHandler,              /* 29 */
    TIM4_IRQHandler,              /* 30 */
    I2C1_EV_IRQHandler,           /* 31 */
    I2C1_ER_IRQHandler,           /* 32 */
    I2C2_EV_IRQHandler,           /* 33 */
    I2C2_ER_IRQHandler,           /* 34 */
    SPI1_IRQHandler,              /* 35 */
    SPI2_IRQHandler,              /* 36 */
    USART1_IRQHandler,            /* 37 */
    USART2_IRQHandler,            /* 38 */
    USART3_IRQHandler,            /* 39 */
    EXTI15_10_IRQHandler,         /* 40 */
    RTC_Alarm_IRQHandler,         /* 41 */
    USBWakeUp_IRQHandler,         /* 42 */
    TIM8_BRK_IRQHandler,          /* 43 */
    TIM8_UP_IRQHandler,           /* 44 */
    TIM8_TRG_COM_IRQHandler,      /* 45 */
    TIM8_CC_IRQHandler,           /* 46 */
    ADC3_IRQHandler,              /* 47 */
    FSMC_IRQHandler,              /* 48 */
    SDIO_IRQHandler,              /* 49 */
    TIM5_IRQHandler,              /* 50 */
    SPI3_IRQHandler,              /* 51 */
    UART4_IRQHandler,             /* 52 */
    UART5_IRQHandler,             /* 53 */
    TIM6_IRQHandler,              /* 54 */
    TIM7_IRQHandler,              /* 55 */
    DMA2_Channel1_IRQHandler,     /* 56 */
    DMA2_Channel2_IRQHandler,     /* 57 */
    DMA2_Channel3_IRQHandler,     /* 58 */
    DMA2_Channel4_5_IRQHandler,   /* 59 */
};

void Reset_Handler(void)
{
    uint32_t *src = &_sidata;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) { *dst++ = *src++; }
    dst = &_sbss;
    while (dst < &_ebss) { *dst++ = 0u; }
    (void)main();
    while (1) {}
}

void Default_Handler(void)
{
    while (1) {}
}
