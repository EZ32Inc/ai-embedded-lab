# STM32F103 I2C Exploratory Assessment v0.1

## Purpose
- record the current bounded assessment of `stm32f103` I2C as a reserved/exploratory path
- avoid treating I2C as the immediate next capability demo by momentum

## Current status
- reserved / exploratory only

## Why it is not the immediate next path
- likely needs pull-up resistors and explicit open-drain electrical assumptions
- higher risk of spending time on bus-electrical setup rather than bounded execution proof
- lower reuse-first value than the already-proven UART / ADC / SPI / PWM / GPIO loopback / EXTI / capture set

## Current repo state
- the repo already contains an older STM32 I2C target/plan shape
- that path is not aligned with the accepted unified self-check method used for current STM32 capability demos
- it should not be treated as part of the current proven unified capability fixture

## What would be needed before making it active
- explicit electrical setup decision
  - pull-ups
  - bus idle assumptions
- bounded success contract
- clear decision whether I2C remains internal self-check only or becomes a stronger external-path proof

## Current decision
- keep I2C reserved / exploratory
- do not start I2C implementation until chosen explicitly as the next bounded path
