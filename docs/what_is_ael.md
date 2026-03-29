# What Is AEL?

## Short Answer

AEL is a hardware validation and orchestration system for running structured tests on DUT boards using probes, instruments, staged execution, and recorded evidence.

## Main Objects

### Boards

Board configs define DUT identity and setup assumptions.

Examples:

- target MCU
- build and flash path
- wiring assumptions
- verification views

Location:

- `configs/boards/*.yaml`

### Instruments

Instruments are bench-side devices used to measure, stimulate, or otherwise interact with a DUT.

Examples:

- `esp32jtag`
- `esp32s3_dev_c_meter`

Locations:

- `configs/instrument_types/*.yaml`
- `configs/instrument_instances/*.yaml`
- `assets_golden/instruments/*/manifest.json`

### Tests

Tests describe validation intent.

Examples:

- signal verification
- UART expectations
- meter-backed validation

Location:

- `tests/plans/*.json`

### Connections

Connections describe how a DUT and bench devices relate for a test.

Examples:

- SWD wiring
- verification net mapping
- DUT-to-instrument signal links
- ground requirements

Primary current source:

- `python3 -m ael inventory describe-connection --board <board> --test <test>`

### Stages

AEL runs work in stages.

Typical stages:

- `plan`
- `pre-flight`
- `run`
- `check`
- `report`

Primary current source:

- `python3 -m ael explain-stage --board <board> --test <test> --stage <stage>`

### User Projects

User projects are lightweight working contexts for a user's own goal — separate from the AEL system baseline.

Examples:

- a first example project for `stm32f411ceu6`
- a project-local setup discussion, assumptions, and next steps

Location:

- `projects/<project_id>/project.yaml`
- `projects/<project_id>/README.md`
- `projects/<project_id>/session_notes.md`

Typical project id shape:

- `<target-or-board>_<goal>`

Examples:

- `stm32f411_first_example`
- `stm32f411_led_blink`
- `stm32f103c6t6_bringup`

The user project domain is distinct from the system domain (`default verification`, board capabilities).
Cross-domain links record which system path a project is anchored to.

## Commands That Show Current Formal Information

System and board/test setup:

- `python3 -m ael inventory describe-test --board <board> --test <test>`
- `python3 -m ael inventory describe-connection --board <board> --test <test>`

User project management:

- `python3 -m ael project create --target-mcu <mcu>`
- `python3 -m ael project list`
- `python3 -m ael project status <id>`
- `python3 -m ael project questions <id>`
- `python3 -m ael project update <id> --set-blocker/--set-status/--set-next-action/...`
- `python3 -m ael project append-note <id> <text>`

Board and system state:

- `python3 -m ael board state <board_id>`
- `python3 -m ael verify-default state`

Instrument information:

- `python3 -m ael instruments describe --id <id>`
- `python3 -m ael instruments doctor --id <id>`

Stage meaning:

- `python3 -m ael explain-stage --board <board> --test <test> --stage <stage>`

Connection consistency:

- `python3 -m ael connection doctor --board <board> --test <test>`

Baseline system health:

- `python3 -m ael verify-default run`

## How Should An Agent Answer AEL Questions Formally?

Use this source order:

1. resolved CLI output
2. current configs, manifests, and specs
3. implementation code for behavior details
4. older docs only as support

Supporting guidance:

- `docs/agent_answering_guide.md`
- `docs/skills/ael_repo_answering_skill.md`

## If You Want The Architecture View

Use:

- `docs/specs/ael_architecture_v0_2.md`

Use this short overview first when the user asks:

- `What is AEL?`
- `How do I use AEL?`

Then go deeper into the architecture spec only if needed.
