/*
 * File: stm32_register.h
 *
 * Common STM32 registers
 */

#ifndef STM32_REGISTER_H
#define STM32_REGISTER_H

#define STM32_REG_CM3_CPUID                   0xe000ed00

#define STM32_REG_CMx_CPUID_PARTNO_CM0        0xc20
#define STM32_REG_CMx_CPUID_PARTNO_CM0P       0xc60
#define STM32_REG_CMx_CPUID_PARTNO_CM3        0xc23
#define STM32_REG_CMx_CPUID_PARTNO_CM4        0xc24
#define STM32_REG_CMx_CPUID_PARTNO_CM7        0xc27
#define STM32_REG_CMx_CPUID_PARTNO_CM33       0xd21
#define STM32_REG_CMx_CPUID_IMPL_ARM          0x41


#define STM32_REG_CM3_FP_CTRL                 0xe0002000  // Flash Patch Control Register
#define STM32_REG_CM3_FP_COMPn(n)             (0xe0002008 + n * 4)
#define STM32_REG_CM3_FP_CTRL_KEY             (1 << 1)
#define STM32_REG_CM7_FP_LAR                  0xe0000fb0
#define STM32_REG_CM7_FP_LAR_KEY              0xc5acce55

#define STM32_REG_CM3_DEMCR                   0xe000edfc
#define STM32_REG_CM3_DEMCR_TRCENA            (1 << 24)
#define STM32_REG_CM3_DEMCR_VC_HARDERR        (1 << 10)
#define STM32_REG_CM3_DEMCR_VC_BUSERR         (1 << 8)
#define STM32_REG_CM3_DEMCR_VC_CORERESET      (1 << 0)
#define STM32_REG_CM3_DWT_COMPn(n)            (0xe0001020 + n * 16)
#define STM32_REG_CM3_DWT_MASKn(n)            (0xe0001024 + n * 16)
#define STM32_REG_CM3_DWT_FUNn(n)             (0xe0001028 + n * 16)

/* Cortex™-M3 Technical Reference Manual */
/* Configurable Fault Status Register */
#define STM32_REG_CFSR                        0xe000ed28

/* Hard Fault Status Register */
#define STM32_REG_HFSR                        0xe000ed2c

/* Debug Halting Control and Status Register */
#define STM32_REG_DFSR                        0xe000ed30
#define STM32_REG_DFSR_HALT                   (1 << 0)
#define STM32_REG_DFSR_BKPT                   (1 << 1)
#define STM32_REG_DFSR_VCATCH                 (1 << 3)
#define STM32_REG_DFSR_EXTERNAL               (1 << 4)
#define STM32_REG_DFSR_CLEAR                  0x0000001f
#define STM32_REG_DHCSR                       0xe000edf0
#define STM32_REG_DHCSR_DBGKEY                (0xa05f << 16)
#define STM32_REG_DHCSR_C_DEBUGEN             (1 << 0)
#define STM32_REG_DHCSR_C_HALT                (1 << 1)
#define STM32_REG_DHCSR_C_STEP                (1 << 2)
#define STM32_REG_DHCSR_C_MASKINTS            (1 << 3)
#define STM32_REG_DHCSR_S_REGRDY              (1 << 16)
#define STM32_REG_DHCSR_S_HALT                (1 << 17)
#define STM32_REG_DHCSR_S_SLEEP               (1 << 18)
#define STM32_REG_DHCSR_S_LOCKUP              (1 << 19)
#define STM32_REG_DHCSR_S_RETIRE_ST           (1 << 24)
#define STM32_REG_DHCSR_S_RESET_ST            (1 << 25)
#define STM32_REG_DCRSR                       0xe000edf4
#define STM32_REG_DCRDR                       0xe000edf8
#define STM32_REG_DEMCR                       0xe000edfc
#define STM32_REG_DEMCR_TRCENA                (1 << 24)

/* MCU Debug Component Registers */
#define STM32_REG_DBGMCU_CR                   0xe0042004  // Debug MCU Configuration Register
#define STM32_REG_DBGMCU_CR_DBG_SLEEP         (1 << 0)
#define STM32_REG_DBGMCU_CR_DBG_STOP          (1 << 1)
#define STM32_REG_DBGMCU_CR_DBG_STANDBY       (1 << 2)
#define STM32_REG_DBGMCU_CR_TRACE_IOEN        (1 << 5)
#define STM32_REG_DBGMCU_CR_TRACE_MODE_ASYNC  (0x00 << 6)

/* Data Watchpoint and Trace (DWT) Registers */
#define STM32_REG_DWT_CTRL                    0xe0001000  // DWT Control Register
#define STM32_REG_DWT_CTRL_NUM_COMP           (1 << 28)
#define STM32_REG_DWT_CTRL_CYC_TAP            (1 << 9)
#define STM32_REG_DWT_CTRL_POST_INIT          (1 << 5)
#define STM32_REG_DWT_CTRL_POST_PRESET        (1 << 1)
#define STM32_REG_DWT_CTRL_CYCCNT_ENA         (1 << 0)
#define STM32_REG_DWT_FUNCTION0               0xe0001028  // DWT Function Register 0
#define STM32_REG_DWT_FUNCTION1               0xe0001038  // DWT Function Register 1
#define STM32_REG_DWT_FUNCTION2               0xe0001048  // DWT Function Register 2
#define STM32_REG_DWT_FUNCTION3               0xe0001058  // DWT Function Register 3

/* Instrumentation Trace Macrocell (ITM) Registers */
#define STM32_REG_ITM_TER                     0xe0000e00  // ITM Trace Enable Register
#define STM32_REG_ITM_TER_PORTS_ALL           (0xffffffff)
#define STM32_REG_ITM_TPR                     0xe0000e40  // ITM Trace Privilege Register
#define STM32_REG_ITM_TPR_PORTS_ALL           (0x0f)
#define STM32_REG_ITM_TCR                     0xe0000e80  // ITM Trace Control Register
#define STM32_REG_ITM_TCR_TRACE_BUS_ID_1      (0x01 << 16)
#define STM32_REG_ITM_TCR_SWO_ENA             (1 << 4)
#define STM32_REG_ITM_TCR_DWT_ENA             (1 << 3)
#define STM32_REG_ITM_TCR_SYNC_ENA            (1 << 2)
#define STM32_REG_ITM_TCR_TS_ENA              (1 << 1)
#define STM32_REG_ITM_TCR_ITM_ENA             (1 << 0)
#define STM32_REG_ITM_TCC                     0xe0000e90  // ITM Trace Cycle Count
#define STM32_REG_ITM_LAR                     0xe0000fb0  // ITM Lock Access Register
#define STM32_REG_ITM_LAR_KEY                 0xc5acce55

/* Trace Port Interface (TPI) Registers */
#define STM32_REG_TPI_CSPSR                   0xe0040004  // TPI Current Parallel Port Size Reg
#define STM32_REG_TPI_CSPSR_PORT_SIZE_1       (0x01 << 0)
#define STM32_REG_TPI_ACPR                    0xe0040010  // TPI Async Clock Prescaler Register
#define STM32_REG_TPI_ACPR_MAX                (0x1fff)
#define STM32_REG_TPI_SPPR                    0xe00400f0  // TPI Selected Pin Protocol Register
#define STM32_REG_TPI_SPPR_SWO_MANCHESTER     (0x01 << 0)
#define STM32_REG_TPI_SPPR_SWO_NRZ            (0x02 << 0)
#define STM32_REG_TPI_FFCR                    0xe0040304  // TPI Formatter and Flush Control Register
#define STM32_REG_TPI_FFCR_TRIG_IN            (0x01 << 8)

/* Application Interrupt and Reset Control Register */
#define STM32_REG_AIRCR                       0xe000ed0c
#define STM32_REG_AIRCR_VECTKEY               0x05fa0000
#define STM32_REG_AIRCR_SYSRESETREQ           0x00000004
#define STM32_REG_AIRCR_VECTRESET             0x00000001

/* ARM Cortex-M7 Processor Technical Reference Manual */
/* Cache Control and Status Register */
#define STM32_REG_CM7_CTR                     0xe000ed7c
#define STM32_REG_CM7_CLIDR                   0xe000ed78
#define STM32_REG_CM7_CCR                     0xe000ed14
#define STM32_REG_CM7_CCR_DC                  (1 << 16)
#define STM32_REG_CM7_CCR_IC                  (1 << 17)
#define STM32_REG_CM7_CSSELR                  0xe000ed84
#define STM32_REG_CM7_DCCSW                   0xe000ef6c
#define STM32_REG_CM7_ICIALLU                 0xe000ef50
#define STM32_REG_CM7_CCSIDR                  0xe000ed80

#endif // STM32_REGISTER_H
