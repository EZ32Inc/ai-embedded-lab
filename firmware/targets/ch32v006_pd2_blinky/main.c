#include <debug.h>

#define LED_GPIO_PORT GPIOD
#define LED_GPIO_PIN  GPIO_Pin_2

static void led_init(void)
{
    GPIO_InitTypeDef gpio = {0};

    RCC_PB2PeriphClockCmd(RCC_PB2Periph_GPIOD, ENABLE);
    gpio.GPIO_Pin = LED_GPIO_PIN;
    gpio.GPIO_Mode = GPIO_Mode_Out_PP;
    gpio.GPIO_Speed = GPIO_Speed_30MHz;
    GPIO_Init(LED_GPIO_PORT, &gpio);

    GPIO_WriteBit(LED_GPIO_PORT, LED_GPIO_PIN, Bit_SET);
}

int main(void)
{
    NVIC_PriorityGroupConfig(NVIC_PriorityGroup_1);
    SystemCoreClockUpdate();
    Delay_Init();
    led_init();

    while(1)
    {
        GPIO_WriteBit(LED_GPIO_PORT, LED_GPIO_PIN, Bit_RESET);
        Delay_Ms(500);
        GPIO_WriteBit(LED_GPIO_PORT, LED_GPIO_PIN, Bit_SET);
        Delay_Ms(500);
    }
}
