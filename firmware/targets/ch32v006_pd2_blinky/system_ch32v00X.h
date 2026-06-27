#ifndef __SYSTEM_CH32V00X_H
#define __SYSTEM_CH32V00X_H

#include <stdint.h>

extern uint32_t SystemCoreClock;

void SystemInit(void);
void SystemCoreClockUpdate(void);

#endif
