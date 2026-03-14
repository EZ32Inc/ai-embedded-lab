# user_project_next_questions_stm32f411_001

Before generating code for the `stm32f411ceu6` first-example project, AEL
should clarify:

- what exact wiring/setup is available on the user's board and bench
- whether the mature `stm32f411ceu6` setup can be reused directly
- what first example the user actually wants:
  - blink
  - gpio signature
  - uart
  - adc
  - spi
- what validation approach should be used first

The current mature `stm32f411ceu6` path should be used as the authority for
what is already validated and what setup is likely reusable.

Generation should be the next stage, not the current one.
