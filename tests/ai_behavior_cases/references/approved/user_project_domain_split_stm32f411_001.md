# user_project_domain_split_stm32f411_001

For the `stm32f411` first-example scenario:

System domain includes:

- `default verification`
- current `stm32f411ceu6` DUT capability support
- the F411 capability anchor note
- inventory/runtime authorities
- system setup and validation knowledge that already exists in AEL

User project domain includes:

- the specific `stm32f411_first_example` project shell
- the user goal
- project-local confirmed facts, assumptions, and unresolved items
- project-local notes and next step

These two domains should stay distinct.
The project may point to the mature F411 system path, but it should not be treated as the system capability anchor itself.
