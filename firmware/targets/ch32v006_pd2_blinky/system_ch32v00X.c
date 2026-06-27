#include <ch32v00X.h>

#define COREWEAVER_HSE_VALUE 12000000u

uint32_t SystemCoreClock = COREWEAVER_HSE_VALUE;
__I uint8_t HBPrescTable[16] = {1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 5, 6, 7, 8};

static void SetSysClockTo_12MHz_HSE(void)
{
    __IO uint32_t startup_counter = 0;
    __IO uint32_t hse_status = 0;

    RCC->PB2PCENR |= RCC_AFIOEN;
    AFIO->PCFR1 |= (1u << 17);

    RCC->CTLR |= RCC_HSEON;

    do
    {
        hse_status = RCC->CTLR & RCC_HSERDY;
        startup_counter++;
    } while((hse_status == 0u) && (startup_counter != HSE_STARTUP_TIMEOUT));

    if((RCC->CTLR & RCC_HSERDY) == RESET)
    {
        AFIO->PCFR1 &= ~(1u << 17);
        RCC->PB2PCENR &= ~RCC_AFIOEN;
        RCC->CTLR &= ~RCC_HSEON;
        return;
    }

    RCC->CFGR0 |= RCC_HPRE_DIV1;
    RCC->CFGR0 &= ~RCC_SW;
    RCC->CFGR0 |= RCC_SW_HSE;

    while((RCC->CFGR0 & RCC_SWS) != 0x04u)
    {
    }

    FLASH->ACTLR = FLASH_ACTLR_LATENCY_0;
    SystemCoreClock = COREWEAVER_HSE_VALUE;
}

void SystemInit(void)
{
    uint32_t tmp;

    FLASH->ACTLR = FLASH_ACTLR_LATENCY_2;
    RCC->CTLR |= 0x00000001u;
    RCC->CFGR0 &= 0x68FF0000u;

    tmp = RCC->CTLR;
    tmp &= 0xFED6FFFBu;
    tmp |= (1u << 20);
    RCC->CTLR = tmp;

    RCC->CTLR &= 0xFFFBFFFFu;
    RCC->CFGR0 &= 0xFFFEFFFFu;
    RCC->INTR = 0x009D0000u;

    GPIO_IPD_Unused();
    SetSysClockTo_12MHz_HSE();
}

void SystemCoreClockUpdate(void)
{
    uint32_t tmp = RCC->CFGR0 & RCC_SWS;
    uint32_t pll_source;

    switch(tmp)
    {
        case 0x00:
            SystemCoreClock = HSI_VALUE;
            break;
        case 0x04:
            SystemCoreClock = COREWEAVER_HSE_VALUE;
            break;
        case 0x08:
            pll_source = RCC->CFGR0 & RCC_PLLSRC;
            SystemCoreClock = (pll_source == 0x00u) ? (HSI_VALUE * 2u) : (COREWEAVER_HSE_VALUE * 2u);
            break;
        default:
            SystemCoreClock = HSI_VALUE;
            break;
    }

    tmp = HBPrescTable[((RCC->CFGR0 & RCC_HPRE) >> 4)];
    if(((RCC->CFGR0 & RCC_HPRE) >> 4) < 8u)
    {
        SystemCoreClock /= tmp;
    }
    else
    {
        SystemCoreClock >>= tmp;
    }
}
