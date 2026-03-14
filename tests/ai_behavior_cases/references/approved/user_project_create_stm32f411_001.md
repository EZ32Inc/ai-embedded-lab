# user_project_create_stm32f411_001

For this request, the first v0.1 AEL action should be to create a lightweight
empty-shell user project, not to generate firmware immediately.

Recommended first response:

- create a project shell under `projects/`
- record the user goal
- anchor the project to the current mature `stm32f411ceu6` path
- record:
  - confirmed fact: the user has a board using `stm32f411ceu6`
  - assumptions: the board is close enough to the mature AEL `stm32f411ceu6` path for a shell-first workflow
  - unresolved items: exact setup/wiring and what first example the user wants
- then ask or propose the next setup/validation questions before code generation

The first response should not jump directly to firmware generation.
